from pathlib import Path
from python_terraform import Terraform
from enum import Enum, auto
from typing import List
import sys
from datetime import timedelta
import time
import json


class RolloutState(Enum):
    ALL_BLUE = "all_blue"
    CANARY_GREEN = "canary_green"
    HALF_AND_HALF = "half_and_half"
    CANARY_BLUE = "canary_blue"
    ALL_GREEN = "all_green"


def agents_appear_to_malfunction(new_agents: List[dict], timeout: timedelta) -> bool:
    time.sleep(1.0)
    return (time.time_ns() % 100) < 1


def get_list_of_agents_to_be_destroyed(plan: dict) -> List[str]:
    return [
        f"bamboo-agent-{resource['change']['before']['id']}"
        for resource in plan["resource_changes"]
        if resource["name"].startswith("bamboo_agent")
        and resource["type"] == "random_string"
        and "delete" in resource["change"]["actions"]
    ]


def stop_bamboo_agents(agents: List[str]):
    for agent in agents:
        time.sleep(0.5)
        print(f"Stopping agent {agent}")


def rollout(working_dir: Path, sequence_states: List[RolloutState]):
    tf = Terraform(working_dir.resolve())

    # Ignore the first state, since is the initial state
    for state in sequence_states[1:]:
        print(f"Rolling out {state.name}")
        agents_running_before_apply = [
            agent["name"] for agent in tf.output()["bamboo_agents"]["value"]
        ]
        rc, stdout, stderr = tf.plan(
            var={"rollout_state": state.value}, out="plan.out", detailed_exitcode=False
        )
        if rc != 0:
            raise RuntimeError(f"Terraform plan failed: {stdout}{stderr}")
        rc, stdout, stderr = tf.cmd("show -json plan.out")
        if rc != 0:
            raise RuntimeError(f"Terraform show failed: {stdout}{stderr}")

        stop_bamboo_agents(
            agents=get_list_of_agents_to_be_destroyed(plan=json.loads(stdout))
        )
        rc, stdout, stderr = tf.cmd("apply plan.out")
        if rc != 0:
            raise RuntimeError(f"Terraform apply failed: {stdout}{stderr}")
        (working_dir / "plan.out").unlink()

        new_agents = [
            agent
            for agent in tf.output()["bamboo_agents"]["value"]
            if agent["name"] not in agents_running_before_apply
        ]
        print("New agents:", new_agents)

        if agents_appear_to_malfunction(new_agents, timeout=timedelta(hours=2)):
            print("New agents seem to malfunction, rolling back.")
            rc, stdout, stderr = tf.cmd(
                f"apply -var rollout_state={sequence_states[0].value} -auto-approve"
            )
            if rc != 0:
                raise RuntimeError(f"Terraform apply failed: {stdout}{stderr}")
            sys.exit(1)


def get_current_state(working_dir: Path) -> RolloutState:
    """
    Will return the string "blue" or "green" depending on
    which plan reports no changes
    """
    tf = Terraform(working_dir.resolve())
    rc, stdout, stderr = tf.plan(
        detailed_exitcode=True, var={"rollout_state": RolloutState.ALL_BLUE.value}
    )
    if rc == 1:
        raise RuntimeError(f"Error when running terraform plan: {stdout}{stderr}")

    if rc == 0:
        return RolloutState.ALL_BLUE

    rc, stdout, stderr = tf.plan(
        detailed_exitcode=True, var={"rollout_state": RolloutState.ALL_GREEN.value}
    )
    if rc == 1:
        raise RuntimeError(f"Error when running terraform plan: {stdout}{stderr}")
    if rc == 0:
        return RolloutState.ALL_GREEN

    raise RuntimeError(
        f"Module in folder {working_dir.resolve()} reports a diff in both blue and green states. "
        "Please ensure it is in a valid state before doing a rollout"
    )


def define_sequence_states(current_state) -> List[RolloutState]:
    """
    Return the sequence of states it needs to go
    through to successfully define a migration

    The initial state is defined so, if a rollback is needed, we know to
    which state we need to roll back.
    """
    if current_state == RolloutState.ALL_BLUE:
        return [
            RolloutState.ALL_BLUE,
            RolloutState.CANARY_GREEN,
            RolloutState.HALF_AND_HALF,
            RolloutState.ALL_GREEN,
        ]
    if current_state == RolloutState.ALL_GREEN:
        return [
            RolloutState.ALL_GREEN,
            RolloutState.CANARY_BLUE,
            RolloutState.HALF_AND_HALF,
            RolloutState.ALL_BLUE,
        ]
    raise AttributeError(f"Current state {current_state} is not a valid starting state")


def main():
    working_dir = Path(__file__).parent / "bamboo_ci_agents"
    tf = Terraform(working_dir.resolve())
    tf.init()

    rc, stdout, stderr = tf.plan(detailed_exitcode=True)
    if rc == 1:
        raise RuntimeError(f"Error when running terraform plan: {stdout}{stderr}")
    if rc == 0:
        print("Module is already at the desired state, nothing to do.")
        sys.exit(0)

    rollout(
        working_dir,
        sequence_states=define_sequence_states(
            current_state=get_current_state(working_dir)
        ),
    )


if __name__ == "__main__":
    main()
