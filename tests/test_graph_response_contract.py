import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage

from fpl_gaffer.graph.nodes import agent_node, response_validation_node
from fpl_gaffer.utils.chains import ResponseValidation


class _FakeChain:
    def __init__(self, response):
        self.response = response
        self.received = None

    async def ainvoke(self, payload):
        self.received = payload
        return self.response


class GraphResponseContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_agent_node_appends_plain_ai_message(self):
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
        }

        with patch("fpl_gaffer.graph.nodes.get_agent_chain", return_value=chain):
            result = await agent_node(state)

        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(result["messages"][0].content, "Plain launch response")
        self.assertIn("retry_feedback", chain.received)
        self.assertEqual(chain.received["retry_feedback"], "")

    async def test_validation_stores_plain_response_without_reappending_messages(self):
        chain = _FakeChain(
            ResponseValidation(validation_passed=True, errors=[], suggestions=[])
        )
        state = {
            "messages": [
                HumanMessage(content="How is my team?"),
                AIMessage(content="Validated response"),
            ],
            "user_id": 123,
            "gameweek_data": {"gameweek": 1},
            "user_data": {
                "team_name": "Test FC",
                "total_points": 10,
                "overall_rank": 1000,
            },
            "retry_count": 0,
        }

        with patch("fpl_gaffer.graph.nodes.get_response_validation_chain", return_value=chain):
            result = await response_validation_node(state)

        self.assertTrue(result["validation_passed"])
        self.assertEqual(result["response"], "Validated response")
        self.assertNotIn("messages", result)  # no duplicate append - agent_node already did it


if __name__ == "__main__":
    unittest.main()
