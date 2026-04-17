# AI Photo Search - AWS Cloud Computing Assignment 3

This project implements a photo album web application that allows users to search photos using natural language and upload new photos with custom labels. It leverages various AWS services to create a serverless, AI-powered search experience.

## Architecture Overview

The system consists of the following components:
- **Frontend**: A React application hosted on S3 (Static Website Hosting).
- **API Layer**: Amazon API Gateway serving as the entry point for search and upload requests.
- **Search Logic**: 
  - **Amazon Lex**: Parses natural language queries to extract keywords.
  - **Lambda (LF2)**: Orchestrates the search by calling Lex and querying OpenSearch.
- **Indexing Logic**:
  - **S3 (B2)**: Stores uploaded photos.
  - **Lambda (LF1)**: Triggered by S3 PUT events; uses **Amazon Rekognition** to detect labels and indexes metadata in OpenSearch.
- **Search Engine**: **Amazon OpenSearch Service** (ElasticSearch) stores and retrieves photo metadata.

## Project Structure

- `backend/lf1/`: Lambda function for indexing photos.
- `backend/lf2/`: Lambda function for searching photos.
- `photo-album/`: React frontend application.
- `swagger.yaml`: API Gateway configuration.

## Development Tasks

1. **OpenSearch Setup**: Launch an Amazon OpenSearch domain named "photos".
2. **Indexing (LF1)**: Implement Lambda to detect labels via Rekognition and store them in OpenSearch.
3. **Search (LF2)**: Implement Lambda to interface with Lex and OpenSearch for natural language search.
4. **API Gateway**: Build the REST API for photo uploads (S3 Proxy) and search queries.
5. **Frontend**: Build a UI for photo uploads with custom labels and search visualization.
6. **CI/CD**: Deploy backend and frontend using AWS CodePipeline.
7. **Infrastructure as Code**: Create a CloudFormation template to provision the stack.

## Getting Started

### Prerequisites
- AWS CLI configured with appropriate permissions.
- Node.js and npm for frontend development.
- Python 3.x for Lambda functions.

### Installation
1. Clone the repository.
2. Navigate to `photo-album/` and run `npm install`.
3. Set up AWS resources as outlined in the tasks above.
