#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Pipeline utilities to support Model Control Plane."""

from typing import List, Optional

from pydantic import BaseModel, PrivateAttr

from zenml.model.model_config import ModelConfig
from zenml.models.model_base_model import ModelConfigModel


class NewModelVersionRequest(BaseModel):
    """Request to create a new model version."""

    class Requester(BaseModel):
        """Requester of a new model version."""

        source: str
        name: str

        def __repr__(self) -> str:
            """Return a string representation of the requester.

            Returns:
                A string representation of the requester.
            """
            return f"{self.source}::{self.name}"

    requesters: List[Requester] = []
    _model_config: Optional[ModelConfig] = PrivateAttr(default=None)

    @property
    def model_config(self) -> ModelConfig:
        """Model config getter.

        Returns:
            The model config.

        Raises:
            RuntimeError: If the model config is not set.
        """
        if self._model_config is None:
            raise RuntimeError("Model config is not set.")
        return self._model_config

    def update_request(
        self,
        model_config: ModelConfigModel,
        requester: "NewModelVersionRequest.Requester",
    ) -> None:
        """Update from Model Config Model object in place.

        Args:
            model_config: Model Config Model object.
            requester: Requester of a new model version.

        Raises:
            ValueError: If the model version name is configured differently by different requesters.
        """
        self.requesters.append(requester)
        if self._model_config is None:
            self._model_config = ModelConfig.parse_obj(model_config)

        if self._model_config.version != model_config.version:
            raise ValueError(
                f"A mismatch of `version` name in model configurations provided for `{model_config.name} detected."
                "Since a new model version is requested for this model, all `version` names must match or left default."
            )

        self._model_config._merge_with_config(model_config)
