import json
import boto3
import os
import requests
import logging

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Lex V2 Runtime client
lex = boto3.client('lexv2-runtime')
s3 = boto3.client('s3')

# Environment variables with defaults
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT', 'https://search-photos-domain.us-east-1.es.amazonaws.com')
LEX_BOT_ID = os.environ.get('LEX_BOT_ID')
LEX_BOT_ALIAS_ID = os.environ.get('LEX_BOT_ALIAS_ID')
OS_USER = os.environ.get('OS_USER', 'admin')
OS_PASS = os.environ.get('OS_PASS', 'Admin123!')
S3_BUCKET = os.environ.get('S3_BUCKET')

def lambda_handler(event, context):
    """
    LF2: search-photos
    Triggered by API Gateway GET /search?q={query}
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Check for empty event which indicates API Gateway misconfiguration
    if not event:
        logger.error("FATAL: Received an empty event. Check API Gateway 'Lambda Proxy Integration' settings.")
        return build_response([], status_code=400, message="Empty event received. Ensure Lambda Proxy Integration is enabled.")

    try:
        # 1. Robust Query Extraction from various potential event structures
        query = None
        
        # Case A: Lambda Proxy Integration (Standard)
        if event.get('queryStringParameters'):
            query = event.get('queryStringParameters', {}).get('q')
        
        # Case B: Non-proxy with common 'params' mapping
        if not query and 'params' in event:
            query = event.get('params', {}).get('querystring', {}).get('q')
            
        # Case C: Direct mapping (e.g., custom mapping template { "q": "$input.params('q')" })
        if not query:
            query = event.get('q')
            
        logger.info(f"Extracted search query: '{query}'")
        
        if not query:
            logger.warning("No search query ('q') found in event parameters.")
            return build_response([])

        # 2. Call Lex to disambiguate the query and extract keywords
        if not LEX_BOT_ID or not LEX_BOT_ALIAS_ID:
            logger.error("Lex configuration missing (LEX_BOT_ID or LEX_BOT_ALIAS_ID env vars).")
            return build_response([], status_code=500, message="Lex configuration missing.")

        logger.info(f"Calling Lex V2 with text: {query}")
        lex_response = lex.recognize_text(
            botId=LEX_BOT_ID,
            botAliasId=LEX_BOT_ALIAS_ID,
            localeId='en_US',
            sessionId='search_session',
            text=query
        )
        logger.info(f"Lex full response: {json.dumps(lex_response)}")

        interpretations = lex_response.get('interpretations', [])
        if not interpretations:
            logger.info("Lex found no interpretations for the query.")
            return build_response([])

        # Use the highest confidence interpretation
        top_interpretation = interpretations[0]
        intent = top_interpretation.get('intent', {})
        intent_name = intent.get('name')
        
        if intent_name == 'FallbackIntent':
            logger.info("Lex reached FallbackIntent - no keywords extracted.")
            return build_response([])

        # Extract keywords from all slots in the triggered intent
        keywords = []
        slots = intent.get('slots', {})
        for slot_name, slot_data in slots.items():
            if slot_data and slot_data.get('value'):
                # Extract the value (interpreted if possible, otherwise original)
                val = slot_data['value'].get('interpretedValue') or slot_data['value'].get('originalValue')
                if val:
                    keywords.append(val.lower())
        
        logger.info(f"Keywords extracted from Lex intent '{intent_name}': {keywords}")

        if not keywords:
            logger.info("No keywords found in intent slots.")
            return build_response([])

        # 3. Query OpenSearch for the keywords
        # We use a single boolean query with 'should' to find any matches with fuzziness
        results = []
        
        query_body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "labels": {
                                    "query": kw,
                                    "fuzziness": "AUTO"
                                }
                            }
                        } for kw in keywords
                    ],
                    "minimum_should_match": 1
                }
            }
        }
        
        # Ensure endpoint doesn't have double slashes if it already has trailing slash
        clean_endpoint = OPENSEARCH_ENDPOINT.rstrip('/')
        url = f"{clean_endpoint}/photos/_search"
        
        logger.info(f"Querying OpenSearch at {url} with body: {json.dumps(query_body)}")
        
        try:
            r = requests.post(
                url, 
                auth=(OS_USER, OS_PASS), 
                json=query_body, 
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            r.raise_for_status()
            
            data = r.json()
            hits = data.get('hits', {}).get('hits', [])
            logger.info(f"OpenSearch returned {len(hits)} hits.")
            
            for hit in hits:
                source = hit['_source']
                bucket = source.get('bucket', S3_BUCKET)
                object_key = source.get('objectKey')
                
                # Generate pre-signed S3 URL for better accessibility of private objects
                try:
                    s3_url = s3.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket, 'Key': object_key},
                        ExpiresIn=3600
                    )
                except Exception as presign_err:
                    logger.error(f"Failed to generate presigned URL for {object_key}: {presign_err}")
                    # Fallback to standard URL if presigning fails
                    s3_url = f"https://{bucket}.s3.amazonaws.com/{object_key}"
                
                results.append({
                    "url": s3_url,
                    "labels": source.get('labels', [])
                })
                
        except Exception as os_err:
            logger.error(f"OpenSearch request failed: {str(os_err)}")
            return build_response([], status_code=502, message="Error querying OpenSearch index.")

        # 4. Deduplicate and return final results
        # Use URL as key for deduplication
        unique_results = list({res['url']: res for res in results}.values())
        logger.info(f"Returning {len(unique_results)} unique results.")
        
        return build_response(unique_results)

    except Exception as e:
        logger.error(f"Internal error in search-photos: {str(e)}", exc_info=True)
        return build_response([], status_code=500, message=f"Internal Server Error: {str(e)}")

def build_response(results, status_code=200, message=None):
    """
    Constructs a Lambda Proxy compatible response.
    """
    body = {'results': results}
    if message:
        body['message'] = message
        
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body)
    }

