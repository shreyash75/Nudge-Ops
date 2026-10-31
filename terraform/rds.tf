# # data "aws_security_group" "eks" {
# #   id = "sg-0ea0aac33fe0217d8"
# # }

# # resource "aws_security_group" "rds" {
# #   name        = "nudge-rds-sg"
# #   description = "Security group for Nudge RDS PostgreSQL"
# # #   vpc_id      = aws_vpc.main.id

# #   ingress {
# #     description     = "PostgreSQL from EKS"
# #     from_port       = 5432
# #     to_port         = 5432
# #     protocol        = "tcp"
# #     security_groups = [data.aws_security_group.eks.id]
# #   }

# #   egress {
# #     from_port   = 0
# #     to_port     = 0
# #     protocol    = "-1"
# #     cidr_blocks = ["0.0.0.0/0"]
# #   }

# #   tags = {
# #     Name = "nudge-rds-sg"
# #   }
# # }

# resource "aws_db_subnet_group" "rds" {
#   name = "nudge-rds-subnet-group"

#   subnet_ids = [
#     aws_subnet.private_1.id,
#     aws_subnet.private_2.id
#   ]

#   tags = {
#     Name = "nudge-rds-subnet-group"
#   }
# }

# resource "aws_secretsmanager_secret" "rds" {
#   name = "nudge/rds"

#   tags = {
#     Name = "nudge-rds"
#   }
# }


# resource "aws_db_instance" "postgres" {
#   identifier = "nudge-postgres"

#   engine         = "postgres"
#   engine_version = "16"

#   instance_class    = "db.t3.micro"
#   allocated_storage = 20
#   storage_type      = "gp3"

#   storage_encrypted = true

#   db_name  = "nudge"
#   username = "postgres"
#   password = var.db_password

#   db_subnet_group_name   = aws_db_subnet_group.rds.name
#   vpc_security_group_ids = [aws_security_group.rds.id]

#   publicly_accessible = false

#   backup_retention_period = 0
#   skip_final_snapshot     = true

#   tags = {
#     Name = "nudge-postgres"
#   }
# }