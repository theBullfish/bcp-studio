"""RBAC ordering and CAN-style permission checks."""

from studio.models import ROLE_ORDER, Role, role_at_least


def test_role_order_is_most_to_least_privileged():
    assert ROLE_ORDER[0] == Role.OWNER
    assert ROLE_ORDER[-1] == Role.VIEWER
    # Each role is at least itself.
    for r in ROLE_ORDER:
        assert role_at_least(r, r)


def test_owner_outranks_everyone():
    for r in ROLE_ORDER:
        assert role_at_least(Role.OWNER, r)


def test_viewer_outranks_no_one_above():
    for r in ROLE_ORDER[:-1]:
        assert not role_at_least(Role.VIEWER, r)


def test_strict_ordering_owner_admin_producer_viewer():
    assert role_at_least(Role.OWNER, Role.ADMIN)
    assert role_at_least(Role.ADMIN, Role.PRODUCER)
    assert not role_at_least(Role.PRODUCER, Role.ADMIN)
    assert not role_at_least(Role.EDITOR, Role.PRODUCER)


def test_producer_can_run_plays_viewer_cannot():
    # "run plays" gate in views is Role.PRODUCER.
    assert role_at_least(Role.PRODUCER, Role.PRODUCER)
    assert role_at_least(Role.ADMIN, Role.PRODUCER)
    assert not role_at_least(Role.VIEWER, Role.PRODUCER)
    assert not role_at_least(Role.CONTRIBUTOR, Role.PRODUCER)


def test_approver_can_approve():
    assert role_at_least(Role.APPROVER, Role.APPROVER)
    assert role_at_least(Role.PRODUCER, Role.APPROVER)
    assert not role_at_least(Role.CONTRIBUTOR, Role.APPROVER)


def test_unknown_role_is_never_privileged():
    assert not role_at_least("NOT_A_ROLE", Role.VIEWER)
    assert not role_at_least(Role.OWNER, "NOT_A_ROLE")
