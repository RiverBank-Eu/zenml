#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from typing import cast

import click
from pipelines.kserve_pytorch_pipeline import kserve_pytorch_pipeline
from rich import print
from steps.deployment_trigger import DeploymentTriggerConfig, deployment_trigger
from steps.model_deployer import custom_kserve_pytorch_deployer
from steps.pytorch_data_loader import (
    PytorchDataLoaderConfig,
    pytorch_data_loader,
)
from steps.pytorch_evaluator import pytorch_evaluator
from steps.pytorch_preprocessing import build_pytorch_preprocessor
from steps.pytorch_trainer import PytorchTrainerConfig, pytorch_trainer

from zenml.integrations.kserve.model_deployers import KServeModelDeployer
from zenml.integrations.kserve.services import KServeDeploymentService


@click.command()
# @click.option(
#    "--deploy",
#    "-d",
#    is_flag=True,
#    help="Run the deployment pipeline to train and deploy a model",
# )
@click.option(
    "--batch-size",
    default=4,
    help="Number of epochs for training (tensorflow hyperparam)",
)
@click.option(
    "--epochs",
    default=3,
    help="Number of epochs for training (tensorflow hyperparam)",
)
@click.option(
    "--lr",
    default=0.01,
    help="Learning rate for training (tensorflow hyperparam, default: 0.003)",
)
@click.option(
    "--momentum",
    default=0.5,
    help="Learning rate for training (tensorflow hyperparam, default: 0.003)",
)
@click.option(
    "--min-accuracy",
    default=0.80,
    help="Minimum accuracy required to deploy the model (default: 0.92)",
)
def main(
    # deploy: bool,
    batch_size: int,
    epochs: int,
    lr: float,
    momentum: float,
    min_accuracy: float,
):
    """Run the Seldon example continuous deployment or inference pipeline

    Example usage:

        python run.py --deploy --min-accuracy 0.80

    """
    model_name = "mnist"
    deployment_pipeline_name = "kserve_pytorch_pipeline"
    deployer_step_name = "kserve_pytorch_model_deployer_step"

    custom_model_deployer = KServeModelDeployer.get_active_model_deployer()

    # Initialize and run a continuous deployment pipeline run
    kserve_pytorch_pipeline(
        build_preprocessor=build_pytorch_preprocessor(),
        build_data_loaders=pytorch_data_loader(
            PytorchDataLoaderConfig(
                train_batch_size=batch_size, test_batch_size=batch_size
            )
        ),
        trainer=pytorch_trainer(
            PytorchTrainerConfig(epochs=epochs, lr=lr, momentum=momentum)
        ),
        evaluator=pytorch_evaluator(),
        deployment_trigger=deployment_trigger(
            config=DeploymentTriggerConfig(
                min_accuracy=min_accuracy,
            )
        ),
        deployer=custom_kserve_pytorch_deployer,
    ).run()

    services = custom_model_deployer.find_model_server(
        pipeline_name=deployment_pipeline_name,
        pipeline_step_name=deployer_step_name,
        model_name=model_name,
    )
    if services:
        service = cast(KServeDeploymentService, services[0])
        if service.is_running:
            print(
                f"The KServe prediction server is running remotely as a Kubernetes "
                f"service and accepts inference requests at:\n"
                f"    {service.prediction_url}\n"
                f"    With the hostname: {service.prediction_hostname}\n"
                f"To stop the service, run "
                f"[italic green]`zenml served-models delete "
                f"{str(service.uuid)}`[/italic green]."
            )
        elif service.is_failed:
            print(
                f"The KServe prediction server is in a failed state:\n"
                f" Last state: '{service.status.state.value}'\n"
                f" Last error: '{service.status.last_error}'"
            )

    else:
        print(
            "No KServe prediction server is currently running. The deployment "
            "pipeline must run first to train a model and deploy it."
        )


if __name__ == "__main__":
    main()
