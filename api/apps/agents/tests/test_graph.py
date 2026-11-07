from django.test import SimpleTestCase, override_settings
from langchain_core.messages import AIMessage

from apps.agents.graph import SAFE_ABSTENTION, run_agent
from apps.agents.models import ToolInvocation
from apps.agents.tools import ToolResult


class FakeModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.bound_tools = None
        self.invocations = 0

    def bind_tools(self, tools, **kwargs):
        self.bound_tools = tools
        return self

    def invoke(self, _messages):
        self.invocations += 1
        return self.responses.pop(0)


class FakeExecutor:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def execute(self, name, arguments):
        self.calls.append((name, arguments))
        return self.result


@override_settings(
    AGENT_MAX_LLM_CALLS=4,
    AGENT_MAX_TOOL_CALLS=3,
    AGENT_MAX_TOTAL_TOKENS=12_000,
)
class AgentGraphTests(SimpleTestCase):
    def test_graph_executes_allowlisted_tool_loop_and_counts_usage(self):
        model = FakeModel(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search_tickets",
                            "args": {"query": "synthetic failure", "limit": 2},
                            "id": "call-1",
                            "type": "tool_call",
                        }
                    ],
                    usage_metadata={
                        "input_tokens": 10,
                        "output_tokens": 2,
                        "total_tokens": 12,
                    },
                ),
                AIMessage(
                    content="The synthetic ticket is open.",
                    usage_metadata={
                        "input_tokens": 15,
                        "output_tokens": 6,
                        "total_tokens": 21,
                    },
                ),
            ]
        )
        executor = FakeExecutor(
            ToolResult(
                content='{"results": [{"code": "TKT-1", "status": "open"}]}',
                outcome=ToolInvocation.Outcome.ALLOWED,
                reason="",
                has_evidence=True,
            )
        )

        result = run_agent(
            question="What happened?", executor=executor, model=model
        )

        self.assertEqual(result["answer"], "The synthetic ticket is open.")
        self.assertEqual(result["llm_calls"], 2)
        self.assertEqual(result["tool_calls"], 1)
        self.assertEqual(result["input_tokens"], 25)
        self.assertEqual(result["output_tokens"], 8)
        self.assertEqual(executor.calls[0][0], "search_tickets")
        self.assertEqual(len(model.bound_tools), 3)

    def test_unsupported_model_answer_is_replaced_with_fixed_abstention(self):
        model = FakeModel([AIMessage(content="Invented unsupported answer")])
        executor = FakeExecutor(
            ToolResult(
                content="{}",
                outcome=ToolInvocation.Outcome.ALLOWED,
                reason="",
                has_evidence=False,
            )
        )

        result = run_agent(question="Reveal secrets", executor=executor, model=model)

        self.assertEqual(result["answer"], SAFE_ABSTENTION)
        self.assertEqual(result["tool_calls"], 0)

    @override_settings(AGENT_MAX_TOOL_CALLS=1)
    def test_tool_budget_never_executes_more_than_configured_limit(self):
        model = FakeModel(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "search_tickets", "args": {"query": "one", "limit": 1}, "id": "call-1", "type": "tool_call"},
                        {"name": "search_tickets", "args": {"query": "two", "limit": 1}, "id": "call-2", "type": "tool_call"},
                    ],
                ),
                AIMessage(content="One authorized result was found."),
            ]
        )
        executor = FakeExecutor(
            ToolResult(
                content='{"results": [{"code": "TKT-1"}]}',
                outcome=ToolInvocation.Outcome.ALLOWED,
                reason="",
                has_evidence=True,
            )
        )

        result = run_agent(question="Search twice", executor=executor, model=model)

        self.assertEqual(len(executor.calls), 1)
        self.assertEqual(result["tool_calls"], 1)

    @override_settings(AGENT_MAX_LLM_CALLS=1)
    def test_llm_call_budget_stops_the_graph_before_a_second_provider_call(self):
        model = FakeModel(
            [AIMessage(
                content="",
                tool_calls=[{
                    "name": "search_tickets",
                    "args": {"query": "synthetic", "limit": 1},
                    "id": "call-1",
                    "type": "tool_call",
                }],
            )]
        )
        executor = FakeExecutor(
            ToolResult(
                content='{"results": [{"code": "TKT-1"}]}',
                outcome=ToolInvocation.Outcome.ALLOWED,
                reason="",
                has_evidence=True,
            )
        )

        result = run_agent(question="Bound the model", executor=executor, model=model)

        self.assertEqual(model.invocations, 1)
        self.assertEqual(result["answer"], SAFE_ABSTENTION)

    @override_settings(AGENT_MAX_TOTAL_TOKENS=10)
    def test_total_token_budget_stops_follow_up_provider_calls(self):
        model = FakeModel(
            [AIMessage(
                content="",
                tool_calls=[{
                    "name": "search_tickets",
                    "args": {"query": "synthetic", "limit": 1},
                    "id": "call-1",
                    "type": "tool_call",
                }],
                usage_metadata={"input_tokens": 9, "output_tokens": 2, "total_tokens": 11},
            )]
        )
        executor = FakeExecutor(
            ToolResult(
                content='{"results": [{"code": "TKT-1"}]}',
                outcome=ToolInvocation.Outcome.ALLOWED,
                reason="",
                has_evidence=True,
            )
        )

        result = run_agent(question="Bound token use", executor=executor, model=model)

        self.assertEqual(model.invocations, 1)
        self.assertEqual(result["answer"], SAFE_ABSTENTION)
        self.assertEqual(result["input_tokens"] + result["output_tokens"], 11)
