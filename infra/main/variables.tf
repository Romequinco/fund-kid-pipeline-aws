variable "region" {
  type    = string
  default = "eu-west-3"
}

variable "alias" {
  description = "Sufijo para que los nombres de bucket sean únicos en todo AWS (el mismo que en bootstrap)."
  type        = string
}

variable "bedrock_model_id" {
  description = "Modelo o perfil de inferencia de Bedrock (D-2.2)."
  type        = string
  default     = ""
}

variable "api_image_tag" {
  type    = string
  default = "latest"
}

variable "dashboard_image_tag" {
  type    = string
  default = "latest"
}

variable "desplegar_dashboard" {
  description = "ECS Express cobra por hora: se enciende para pruebas y la exposición (D-5.2)."
  type        = bool
  default     = true
}
