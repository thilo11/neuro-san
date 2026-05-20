
# Copyright © 2023-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# END COPYRIGHT

from logging import Logger
from logging import getLogger
from typing import Any
from typing import Dict
from typing import List
from typing import Set

from neuro_san.internals.validation.network.abstract_network_validator import AbstractNetworkValidator


class FunctionParametersNetworkValidator(AbstractNetworkValidator):
    """
    Validates that function.parameters in each agent spec follows a valid
    JSON Schema structure.  Catches common HOCON authoring mistakes such as
    accidentally nesting an extra "parameters" object inside
    function.parameters.
    """

    VALID_PARAMETER_KEYS: Set[str] = {
        "type", "properties", "required", "description",
        "additionalProperties", "enum", "default", "items",
    }

    def validate_name_to_spec_dict(self, name_to_spec: Dict[str, Any]) -> List[str]:
        """
        Validate function.parameters for every agent in the network.

        :param name_to_spec: The name -> agent spec dictionary to validate
        :return: List of error messages
        """
        logger: Logger = getLogger(self.__class__.__name__)
        errors: List[str] = []

        logger.info("Validating function.parameters schemas...")

        for agent_name, agent in name_to_spec.items():
            errors.extend(self._validate_agent_parameters(agent_name, agent))

        if len(errors) > 0:
            logger.warning(str(errors))

        return errors

    @classmethod
    def _validate_agent_parameters(cls, agent_name: str, agent: Dict[str, Any]) -> List[str]:
        """
        Validate the function.parameters block of a single agent.

        :param agent_name: The name of the agent being validated
        :param agent: The agent spec dictionary
        :return: A list of error messages
        """
        errors: List[str] = []

        function: Any = agent.get("function")
        if not isinstance(function, dict):
            return errors

        parameters: Any = function.get("parameters")
        if parameters is None:
            return errors

        if not isinstance(parameters, dict):
            errors.append(
                f"{agent_name} 'function.parameters' must be a dict,"
                f" got {type(parameters).__name__}."
            )
            return errors

        errors.extend(cls._validate_parameters_schema(agent_name, parameters))
        return errors

    @classmethod
    def _validate_parameters_schema(
        cls,
        agent_name: str,
        parameters: Dict[str, Any],
    ) -> List[str]:
        """
        Check the parameters dict for structural problems.

        :param agent_name: The name of the agent being validated
        :param parameters: The function.parameters dictionary
        :return: A list of error messages
        """
        errors: List[str] = []

        # Detect nested "parameters" inside parameters — the #690 bug pattern.
        if "parameters" in parameters:
            errors.append(
                f"{agent_name} 'function.parameters' contains a nested 'parameters' key. "
                f"This is likely an accidental extra level of nesting. "
                f"Expected keys inside 'function.parameters' are: "
                f"type, properties, required."
            )

        # When type is "object", properties should be present.
        param_type: Any = parameters.get("type")
        if param_type == "object" and "properties" not in parameters:
            errors.append(
                f"{agent_name} 'function.parameters' has type \"object\" "
                f"but is missing 'properties'."
            )

        # Check for unexpected keys that suggest a structural mistake.
        unexpected: Set[str] = set(parameters.keys()) - cls.VALID_PARAMETER_KEYS
        if unexpected:
            errors.append(
                f"{agent_name} 'function.parameters' contains unexpected keys: "
                f"{sorted(unexpected)}. "
                f"Expected keys are: {sorted(cls.VALID_PARAMETER_KEYS)}."
            )

        return errors
