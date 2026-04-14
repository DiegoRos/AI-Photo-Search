import json
import urllib.parse
import boto3
import os
import requests
import logging

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')
opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT', 'https://search-photos-domain.us-east-1.es.amazonaws.com')

def lambda_handler(event, context):
    """
    LF1: index-photos
    Triggered by S3 PUT event.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Get bucket and key from event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
        event_size = event['Records'][0]['s3']['object'].get('size', -1)
        logger.info(f"Processing object: {key} from bucket: {bucket}. Event size: {event_size}")
        
        # Quick check if event says size is 0
        if event_size == 0:
            logger.warning(f"File {key} is reported as 0 bytes in the event. Skipping Rekognition.")
            return {
                'statusCode': 200,
                'body': json.dumps('Skipped empty file based on event size')
            }
        
        # Get metadata from S3
        logger.info(f"Fetching S3 head_object for {key}")
        response = s3.head_object(Bucket=bucket, Key=key)
        content_length = int(response.get('ContentLength', 0))
        logger.info(f"S3 response ContentLength: {content_length}")
        
        # Check if file is empty via head_object
        if content_length == 0:
            logger.warning(f"File {key} is 0 bytes according to S3. Skipping Rekognition.")
            return {
                'statusCode': 200,
                'body': json.dumps('Skipped empty file based on S3 ContentLength')
            }
            
        logger.info(f"S3 response metadata: {response.get('Metadata')}")
        
        # x-amz-meta-customLabels comes as 'customlabels' in Boto3
        custom_labels = response['Metadata'].get('customlabels', '')
        labels_list = [l.strip() for l in custom_labels.split(',')] if custom_labels else []
        logger.info(f"Custom labels extracted: {labels_list}")
        
        # Detect labels using Rekognition for supported formats (JPEG, PNG, BMP, WebP)
        rek_labels = []
        supported_rek_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
        if key.lower().endswith(supported_rek_formats):
            logger.info(f"Calling Rekognition detect_labels for {key}")
            try:
                rek_response = rekognition.detect_labels(
                    Image={'S3Object': {'Bucket': bucket, 'Name': key}},
                    MaxLabels=10,
                    MinConfidence=75
                )
                rek_labels = [label['Name'] for label in rek_response['Labels']]
                logger.info(f"Rekognition detected labels: {rek_labels}")
            except Exception as rek_err:
                logger.warning(f"Rekognition failed for {key}: {rek_err}")
        else:
            logger.info(f"Format for {key} not supported by Rekognition. Skipping detect_labels.")
        
        for label_name in rek_labels:
            labels_list.append(label_name)
            
        # Clean and deduplicate labels
        labels_list = list(set([l.lower() for l in labels_list]))
        logger.info(f"Final labels list: {labels_list}")
        
        # Prepare OpenSearch document
        document = {
            "objectKey": key,
            "bucket": bucket,
            "createdTimestamp": response['LastModified'].isoformat(),
            "labels": labels_list
        }
        logger.info(f"Indexing document: {json.dumps(document)}")
        
        # Post to OpenSearch
        url = f"{opensearch_endpoint}/photos/_doc"
        headers = {"Content-Type": "application/json"}
        os_user = os.environ.get('OS_USER', 'admin')
        os_pass = os.environ.get('OS_PASS', 'Admin123!')
        
        logger.info(f"Posting to OpenSearch at {url}")
        r = requests.post(url, auth=(os_user, os_pass), json=document, headers=headers)
        logger.info(f"OpenSearch response status: {r.status_code}")
        logger.info(f"OpenSearch response body: {r.text}")
        r.raise_for_status()
        
        logger.info(f"Successfully indexed photo {key}")
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully indexed photo')
        }
    except Exception as e:
        logger.error(f"Error processing object {key if 'key' in locals() else 'unknown'} from bucket {bucket if 'bucket' in locals() else 'unknown'}")
        logger.error(f"Exception: {str(e)}", exc_info=True)
        raise e
