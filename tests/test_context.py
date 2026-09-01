from contextflow.core.context import ContextObject


def test_context_object_defaults():
    obj = ContextObject(content="hello world", source="test")
    assert obj.id
    assert obj.type == "document"
    assert obj.freshness == 1.0
    assert obj.is_visible_to("anyone")  # no permissions set -> public


def test_context_object_permissions():
    obj = ContextObject(content="secret", source="test", permissions=["alice"])
    assert obj.is_visible_to("alice")
    assert not obj.is_visible_to("bob")
