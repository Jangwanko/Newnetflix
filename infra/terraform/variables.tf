variable "project_name" {
  type        = string
  description = "Project name prefix."
  default     = "myflix"
}

variable "environment" {
  type        = string
  description = "Environment name."
  default     = "prod"
}

variable "aws_region" {
  type        = string
  description = "AWS region."
  default     = "ap-northeast-2"
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR."
  default     = "10.30.0.0/16"
}

variable "eks_version" {
  type        = string
  description = "EKS Kubernetes version."
  default     = "1.31"
}

variable "node_instance_types" {
  type        = list(string)
  description = "EKS node group instance types."
  default     = ["t3.large"]
}

variable "node_desired_size" {
  type        = number
  description = "Desired node count."
  default     = 2
}

variable "node_min_size" {
  type        = number
  description = "Minimum node count."
  default     = 2
}

variable "node_max_size" {
  type        = number
  description = "Maximum node count."
  default     = 5
}

variable "db_name" {
  type        = string
  description = "RDS database name."
  default     = "myflix"
}

variable "db_username" {
  type        = string
  description = "RDS database username."
  default     = "myflix_user"
}

variable "db_instance_class" {
  type        = string
  description = "RDS instance class."
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type        = number
  description = "RDS storage size (GiB)."
  default     = 30
}

variable "db_multi_az" {
  type        = bool
  description = "Enable RDS Multi-AZ."
  default     = false
}

variable "secret_name" {
  type        = string
  description = "Secrets Manager key name for application secrets."
  default     = "prod/myflix"
}

variable "domain_name" {
  type        = string
  description = "Public domain for service (optional)."
  default     = ""
}

variable "enable_iac_apply" {
  type        = bool
  description = "Safety guard. Must be true to allow terraform plan/apply."
  default     = false
}
