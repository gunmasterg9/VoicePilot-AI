"""Focused regression tests for issues found during the Phase 5 audit."""
import os
import unittest
from unittest.mock import patch

from core.safety import is_path_safe_for_deletion, mask_sensitive_data


class TestPathTraversalAudit(unittest.TestCase):
    def test_rejects_traversal_components_before_resolution(self):
        safe, reason = is_path_safe_for_deletion("folder/../target.txt")
        self.assertFalse(safe)
        self.assertIn("traversal", reason.lower())

    def test_masks_common_credential_assignments(self):
        samples = [
            ('api_key: abcdef123456', 'abcdef123456'),
            ('"password": "very-secret-value"', 'very-secret-value'),
            ('Authorization: Bearer abcdefghijklmnop', 'abcdefghijklmnop'),
            ('token=opaque-token-value', 'opaque-token-value'),
            ('sk-proj-1234567890abcdef', 'sk-proj-1234567890abcdef'),
        ]
        for raw, secret in samples:
            with self.subTest(raw=raw):
                masked = mask_sensitive_data(raw)
                self.assertNotIn(secret, masked)
                self.assertIn("MASKED", masked)


class TestDestructiveConfirmationAudit(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "registry imports Windows desktop automation dependencies")
    def test_destructive_tool_without_confirmation_is_blocked(self):
        # Import lazily so the pure path/masking tests can still run in
        # headless environments where desktop automation dependencies fail.
        from tools.base import ToolPermission, ToolSpec
        from tools.registry import execute_tool

        action = unittest.mock.Mock(return_value="deleted")
        spec = ToolSpec(
            name="delete_path", description="test", function=action,
            parameters={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            permission=ToolPermission.DESTRUCTIVE,
        )
        with patch("tools.registry.TOOLS", {"delete_path": action}), patch(
            "tools.registry.TOOL_SPECS", {"delete_path": spec}
        ):
            result = execute_tool("delete_path", {"path": "example.txt"})
        self.assertFalse(result.success)
        self.assertIn("confirmation", str(result).lower())
        action.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "registry imports Windows desktop automation dependencies")
    def test_confirmation_callback_exception_fails_closed(self):
        from tools.base import ToolPermission, ToolSpec
        from tools.registry import execute_tool

        action = unittest.mock.Mock(return_value="deleted")
        spec = ToolSpec(
            name="delete_path", description="test", function=action,
            parameters={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            permission=ToolPermission.DESTRUCTIVE,
        )
        with patch("tools.registry.TOOLS", {"delete_path": action}), patch(
            "tools.registry.TOOL_SPECS", {"delete_path": spec}
        ):
            result = execute_tool(
                "delete_path", {"path": "example.txt"},
                confirm_callback=lambda *_: (_ for _ in ()).throw(RuntimeError("dialog failed")),
            )
        self.assertFalse(result.success)
        action.assert_not_called()


if __name__ == "__main__":
    unittest.main()
