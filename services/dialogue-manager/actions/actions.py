from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher


class ActionGetSoilMoisture(Action):
    def name(self) -> Text:
        return "action_get_soil_moisture"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # In a full flow, this queries Core API GraphQL
        dispatcher.utter_message(
            text="Your field volumetric water content is currently 32.4% (Optimal). No immediate irrigation needed for the next 24 hours."
        )
        return []


class ActionGetCropAdvisory(Action):
    def name(self) -> Text:
        return "action_get_crop_advisory"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(
            text="[NOW] Scout border rows for early aphid presence. [NEXT] Spray neem oil 5ml/L if count > 5/leaf. [WHY] High humidity (78%) and warm temperatures favor aphid reproduction."
        )
        return []
