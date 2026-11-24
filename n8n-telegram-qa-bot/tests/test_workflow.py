import json
import pathlib
import unittest

WORKFLOW_PATH = pathlib.Path(__file__).resolve().parent.parent / "workflow.json"
QA_PATH = pathlib.Path(__file__).resolve().parent.parent / "sample_qa.json"


class TestWorkflowStructure(unittest.TestCase):
    def test_workflow_json_valid_and_connected(self):
        data = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        self.assertIn("nodes", data)
        self.assertIn("connections", data)

        node_names = {node["name"] for node in data["nodes"]}
        expected_nodes = {
            "Telegram Trigger",
            "Match Curated Q&A",
            "Deterministic Match Found?",
            "Send Matched Reply",
            "AI Grounded Q&A Matcher",
            "Format AI / Fallback Reply",
            "Send AI or Fallback Reply",
        }
        self.assertEqual(expected_nodes, node_names)

        # Verify every connection target exists in nodes
        for source, branches in data["connections"].items():
            self.assertIn(source, node_names)
            for outputs in branches.get("main", []):
                for target in outputs:
                    self.assertIn(target["node"], node_names)

    def test_sample_qa_schema(self):
        qa_items = json.loads(QA_PATH.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(qa_items), 4)
        for item in qa_items:
            self.assertTrue(item["id"])
            self.assertIsInstance(item["keywords"], list)
            self.assertTrue(item["question"])
            self.assertTrue(item["answer"])


if __name__ == "__main__":
    unittest.main()
