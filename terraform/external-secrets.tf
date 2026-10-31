resource "aws_iam_policy" "external_secrets" {
  name = "ExternalSecretsPolicy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"

        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]

        Resource = "*"
      }
    ]
  })
}