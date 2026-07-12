import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage

from fpl_gaffer.graph.nodes import message_generation_node, response_validation_node
from fpl_gaffer.utils.chains import ResponseValidation


class _FakeChain:
    def __init__(self, response):
        self.response = response
        self.received = None

    async def ainvoke(self, payload):
        self.received = payload
        return self.response


class GraphResponseContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_message_generation_stores_plain_text_response(self):
        chain = _FakeChain(AIMessage(content="Plain launch response"))
        state = {
            "messages": [HumanMessage(content="How is my team?")],
            "user_id": 123,
            "gameweek_data": {"gameweek": 1},
            "user_data": {
                "team_name": "Test FC",
                "total_points": 10,
                "overall_rank": 1000,
            },
            "tool_results": {},
        }

        with patch("fpl_gaffer.graph.nodes.get_gaffer_response_chain", return_value=chain):
            result = await message_generation_node(state)

        self.assertEqual(result["response"], "Plain launch response")
        self.assertIsInstance(result["response"], str)

    async def test_validation_appends_ai_message_after_success(self):
        chain = _FakeChain(
            ResponseValidation(
                validation_passed=True,
                errors=[],
                suggestions=[],
            )
        )
        state = {
            "messages": [HumanMessage(content="How is my team?")],
            "response": "Validated response",
            "user_id": 123,
            "gameweek_data": {"gameweek": 1},
            "user_data": {
                "team_name": "Test FC",
                "total_points": 10,
                "overall_rank": 1000,
            },
            "tool_results": {},
            "retry_count": 0,
        }

        with patch("fpl_gaffer.graph.nodes.get_response_validation_chain", return_value=chain):
            result = await response_validation_node(state)

        self.assertTrue(result["validation_passed"])
        self.assertIsInstance(result["messages"], AIMessage)
        self.assertEqual(result["messages"].content, "Validated response")


if __name__ == "__main__":
    unittest.main()
