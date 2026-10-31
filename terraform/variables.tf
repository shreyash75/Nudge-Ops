variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
}

variable "cluster_name" {
  description = "EKS Cluster Name"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
}

variable "public_subnet_1_cidr" {
  description = "CIDR for Public Subnet 1"
  type        = string
}

variable "public_subnet_2_cidr" {
  description = "CIDR for Public Subnet 2"
  type        = string
}

variable "private_subnet_1_cidr" {
  description = "CIDR for Private Subnet 1"
  type        = string
}

variable "private_subnet_2_cidr" {
  description = "CIDR for Private Subnet 2"
  type        = string
}

variable "node_instance_type" {
  description = "Worker node instance type"
  type        = string
}

variable "desired_nodes" {
  description = "Desired number of worker nodes"
  type        = number
}

variable "db_password" {
  description = "Password for the RDS PostgreSQL instance"
  type        = string
  sensitive   = true
}