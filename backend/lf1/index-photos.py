import json
import urllib.parse
import boto3
import os
import requests

s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')
opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT', 'https://search-photos-domain.us-east-1.es.amazonaws.com')

def lambda_handler(event, context):
    """
    LF1: index-photos
    Triggered by S3 PUT event.
    """
    # Prefer bucket from environment variable, fall back to event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    if not bucket:
        print("S3 bucket not found in environment or event")
        return {
            'statusCode': 400,
            'body': json.dumps('S3 bucket not found')
        }
    
    try:
        # Get metadata from S3
        response = s3.head_object(Bucket=bucket, Key=key)
        custom_labels = response['Metadata'].get('customlabels', '')
        labels_list = [l.strip() for l in custom_labels.split(',')] if custom_labels else []
        
        # Detect labels using Rekognition
        rek_response = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxLabels=10,
            MinConfidence=75
        )
        
        for label in rek_response['Labels']:
            labels_list.append(label['Name'])
            
        labels_list = list(set([l.lower() for l in labels_list]))
        
        # Prepare OpenSearch document
        document = {
            "objectKey": key,
            "bucket": bucket,
            "createdTimestamp": response['LastModified'].isoformat(),
            "labels": labels_list
        }
        
        # Post to OpenSearch
        url = f"{opensearch_endpoint}/photos/_doc"
        headers = {"Content-Type": "application/json"}
        os_user = os.environ.get('OS_USER', 'admin')
        os_pass = os.environ.get('OS_PASS', 'Admin123!')
        
        r = requests.post(url, auth=(os_user, os_pass), json=document, headers=headers)
        r.raise_for_status()
        
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully indexed photo')
        }
    except Exception as e:
        print(f"Error processing object {key} from bucket {bucket}. Event: {json.dumps(event)}")
        raise e
