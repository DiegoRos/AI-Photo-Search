import json
import boto3
import os
import requests

lex = boto3.client('lexv2-runtime')
opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT', 'https://search-photos-domain.us-east-1.es.amazonaws.com')

def lambda_handler(event, context):
    """
    LF2: search-photos
    Triggered by API Gateway GET /search
    """
    query = event['queryStringParameters']['q']
    
    # Call Lex to extract keywords
    response = lex.recognize_text(
        botId=os.environ['LEX_BOT_ID'],
        botAliasId=os.environ['LEX_BOT_ALIAS_ID'],
        localeId='en_US',
        sessionId='search_session',
        text=query
    )
    
    keywords = []
    if 'sessionState' in response and 'intent' in response['sessionState']['intent']:
        slots = response['sessionState']['intent']['slots']
        for slot_name, slot_data in slots.items():
            if slot_data and slot_data.get('value'):
                keywords.append(slot_data['value']['interpretedValue'])
                
    if not keywords:
        keywords = [query]
        
    keywords = [k.lower() for k in keywords]
    
    # Query OpenSearch
    results = []
    os_user = os.environ.get('OS_USER', 'admin')
    os_pass = os.environ.get('OS_PASS', 'Admin123!')

    for keyword in keywords:
        url = f"{opensearch_endpoint}/photos/_search?q=labels:{keyword}"
        r = requests.get(url, auth=(os_user, os_pass))
        if r.status_code == 200:
            data = r.json()
            if 'hits' in data and 'hits' in data['hits']:
                for hit in data['hits']['hits']:
                    source = hit['_source']
                    # Use bucket from environment variable for consistent URL generation
                    bucket = os.environ.get('S3_BUCKET')
                    s3_url = f"https://{bucket}.s3.amazonaws.com/{source['objectKey']}"
                    results.append({
                        "url": s3_url,
                        "labels": source['labels']
                    })
                
    # Deduplicate results based on URL
    unique_results = list({r['url']: r for r in results}.values())
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'results': unique_results
        })
    }
