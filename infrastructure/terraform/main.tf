terraform {
  required_version = ">= 1.6"
  
  backend "s3" {
    bucket         = "potential-parakeet-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "potential-parakeet"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
