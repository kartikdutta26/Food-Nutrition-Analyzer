"""M5.3 recognition yields hypotheses, never an M3 request or nutrition result."""
from uuid import uuid4

from agentic_ai.adapters.vision_handoff import validate_recognition_result
from agentic_ai.clients.ollama_vision_client import OllamaVisionClient, VisionInferenceReply
from agentic_ai.schemas.vision import (CandidateFoodGroup, FoodHypothesis, HARD_UNCERTAINTY,
                                      ImageFoodRecognitionResult, VisionModelProvenance,
                                      required_confirmation_questions)
from agentic_ai.schemas.vision_inference import PROMPT_VERSION, RawVisionResponse
from agentic_ai.tools.image_input import ImageInputError, preprocess_image
from agentic_ai.vision_config import VisionContractSettings
from agentic_ai.vision_errors import VisionContractError
from agentic_ai.vision_runtime_config import VisionRuntimeSettings
from agentic_ai.vision_runtime_errors import VisionRuntimeError
from agentic_ai.vision_validation import parse_metadata


class ImageFoodRecognitionAgent:
    def __init__(self, settings=None, client=None):
        try:
            selected = settings
            if selected is None:
                selected = client.settings if isinstance(client, OllamaVisionClient) else VisionRuntimeSettings()
            self.settings = VisionRuntimeSettings.model_validate(selected)
            if isinstance(client, OllamaVisionClient) and client.settings != self.settings:
                raise VisionRuntimeError("invalid_configuration")
            self.client = client if client is not None else OllamaVisionClient(self.settings)
        except VisionRuntimeError:
            raise
        except Exception:
            raise VisionRuntimeError("invalid_configuration") from None

    def analyze(self, path):
        try:
            # The default fixed 1024 fit policy is required by unchanged M5.1.
            image = preprocess_image(path)
            reply = self.client.analyze(image)
            if not isinstance(reply, VisionInferenceReply) or not isinstance(reply.content, str):
                raise VisionRuntimeError("invalid_response")
            provenance = VisionModelProvenance.model_validate(reply.provenance)
            if (provenance.model_tag != self.settings.model or provenance.prompt_version != PROMPT_VERSION
                    or provenance.inference != self.settings.inference_configuration()):
                raise VisionRuntimeError("invalid_response")
            raw = parse_metadata(reply.content, RawVisionResponse, VisionContractSettings(),
                                 limit=self.settings.max_model_output_bytes, code="invalid_recognition")
            groups, reasons = [], set(raw.uncertainty_reasons)
            for index, group in enumerate(raw.groups, 1):
                group_reasons = set(group.uncertainty_reasons) | {"identity_unconfirmed", "unknown_preparation"}
                if len(group.labels) > 1:
                    group_reasons.add("ambiguous_identity")
                reasons.update(group_reasons)
                groups.append(CandidateFoodGroup(group_id=f"group-{index}", location=group.location,
                              candidates=tuple(FoodHypothesis(candidate_id=f"food-{index}-{rank}", rank=rank, label=label)
                                               for rank, label in enumerate(group.labels, 1)),
                              uncertainty_reasons=tuple(sorted(group_reasons))))
            if len(groups) > 1:
                reasons.add("multiple_foods")
            status = raw.status
            if groups and reasons & HARD_UNCERTAINTY:
                status = "uncertain"
            result = ImageFoodRecognitionResult(result_id="vision-"+uuid4().hex[:24], revision=1,
                         status=status, image=image.image, preprocessing=image.preprocessing,
                         model_provenance=provenance, groups=tuple(groups), uncertainty_reasons=tuple(sorted(reasons)),
                         questions=required_confirmation_questions(groups, status))
            return validate_recognition_result(result)
        except (ImageInputError, VisionRuntimeError):
            raise
        except (VisionContractError, ValueError, TypeError):
            raise VisionRuntimeError("invalid_model_output") from None
        except Exception:
            raise VisionRuntimeError("inference_failed") from None
