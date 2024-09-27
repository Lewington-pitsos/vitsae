output "ecs_cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.ml_cluster.id
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.ml_service.name
}
