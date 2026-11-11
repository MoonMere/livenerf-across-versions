"""The void rule for server-side tools (design file 判断标准.md, section 1, rule 3; checklist C17): the count
is read from the result line, and an ask that has one is void before the model and turn rules are looked at.

    CCV_AUTHOR_REPO=<the author's repo> python -B -m unittest discover -s tests     (from the program folder)
"""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ccversions import extract, grade  # noqa: E402


def fields(**over):
    f = {"has_result": True, "is_error": False, "stop_reason": "end_turn", "api_key_source": "none",
         "is_using_overage": False, "tools_ran": 0, "subagent_events": 0, "canary_hits": 0,
         "server_tool_requests": 0, "requested_model": extract.MODEL, "served_models": [extract.MODEL],
         "num_turns": 1, "tool_rounds": 0, "context_tokens": 100}
    f.update(over)
    return f


RECORD = {"status": grade.RUNNER_OK, "returncode": 0, "mode": "stock_blocked"}


class ServerToolTests(unittest.TestCase):
    def test_the_count_is_read_from_both_places_of_the_result_line(self):
        self.assertEqual(extract.server_tool_requests(None), 0)
        self.assertEqual(extract.server_tool_requests({"usage": {"server_tool_use": {"web_search_requests": 0,
                                                                                    "web_fetch_requests": 0}}}), 0)
        self.assertEqual(extract.server_tool_requests({"usage": {"server_tool_use": {"web_search_requests": 2,
                                                                                    "web_fetch_requests": 1}}}), 3)
        self.assertEqual(extract.server_tool_requests({"modelUsage": {"m": {"webSearchRequests": 1}}}), 1)

    def test_an_ask_with_a_server_side_tool_is_void(self):
        limit = lambda system, prompt: 10_000  # noqa: E731
        self.assertEqual(grade.integrity(RECORD, fields(), "s", "p", limit), ("ok", None))
        self.assertEqual(grade.integrity(RECORD, fields(server_tool_requests=1), "s", "p", limit),
                         ("void", "server_tool"))
        # it comes before the rules on the served model and on the number of turns
        self.assertEqual(grade.integrity(RECORD, fields(server_tool_requests=1, served_models=["other"],
                                                        num_turns=3), "s", "p", limit), ("void", "server_tool"))
        # and after a tool that really ran
        self.assertEqual(grade.integrity(RECORD, fields(server_tool_requests=1, tools_ran=1), "s", "p", limit),
                         ("void", "tool_ran"))


if __name__ == "__main__":
    unittest.main()
