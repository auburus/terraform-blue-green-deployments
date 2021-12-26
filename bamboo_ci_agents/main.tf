
variable "rollout_state" {
  type = string
  validation {
    condition     = contains(["all_blue", "canary_green", "half_and_half", "canary_blue", "all_green"], var.rollout_state)
    error_message = "Invalid value. Must be one of [all_blue, canary_green, half_and_half, canary_blue, all_green]."
  }
}

locals {
  agents_quantity = {
    "all_blue" = {
      "m" = {
        "blue"  = 5,
        "green" = 0,
      },
      "xl" = {
        "blue"  = 2,
        "green" = 0,
      },
    },
    "canary_green" = {
      "m" = {
        "blue"  = 4,
        "green" = 1,
      },
      "xl" = {
        "blue"  = 2,
        "green" = 0,
      },
    },
    "half_and_half" = {
      "m" = {
        "blue"  = 3,
        "green" = 2,
      },
      "xl" = {
        "blue"  = 1,
        "green" = 1,
      },
    },
    "canary_blue" = {
      "m" = {
        "blue"  = 1,
        "green" = 4,
      },
      "xl" = {
        "blue"  = 0,
        "green" = 2,
      },
    },
    "all_green" = {
      "m" = {
        "blue"  = 0,
        "green" = 5,
      },
      "xl" = {
        "blue"  = 0,
        "green" = 2,
      },
    },
  }

  bamboo_agents_names = {
    "m" = {
      "blue"  = [for rand_id in random_string.bamboo_agent_m_blue : "bamboo-agent-m-${rand_id.result}"],
      "green" = [for rand_id in random_string.bamboo_agent_m_green : "bamboo-agent-m-${rand_id.result}"],
    },
    "xl" = {
      "blue"  = [for rand_id in random_string.bamboo_agent_xl_blue : "bamboo-agent-xl-${rand_id.result}"],
      "green" = [for rand_id in random_string.bamboo_agent_xl_green : "bamboo-agent-xl-${rand_id.result}"],
    },
  }
}


resource "random_string" "bamboo_agent_m_blue" {
  count   = local.agents_quantity[var.rollout_state]["m"]["blue"]
  length  = 4
  special = false
  upper   = false
}
resource "random_string" "bamboo_agent_m_green" {
  count   = local.agents_quantity[var.rollout_state]["m"]["green"]
  length  = 4
  special = false
  upper   = false
}
resource "random_string" "bamboo_agent_xl_blue" {
  count   = local.agents_quantity[var.rollout_state]["xl"]["blue"]
  length  = 4
  special = false
  upper   = false
}
resource "random_string" "bamboo_agent_xl_green" {
  count   = local.agents_quantity[var.rollout_state]["xl"]["green"]
  length  = 4
  special = false
  upper   = false
}

output "bamboo_agents" {
  value = concat(
    [for agent in concat(local.bamboo_agents_names["m"]["blue"], local.bamboo_agents_names["m"]["green"]) : { "name" : agent, "size" : "m" }],
    [for agent in concat(local.bamboo_agents_names["xl"]["blue"], local.bamboo_agents_names["xl"]["green"]) : { "name" : agent, "size" : "xl" }],
  )
}