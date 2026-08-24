"""Pure exact owner authorization kernel for accepted-main root transitions.

This module intentionally performs no I/O and executes no candidate code.  The
accepted-main reconciler supplies GitHub API objects, repository identity, the
server Date header, and values computed from blobs through trusted git plumbing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import posixpath
import re
from typing import Any, Iterable, Mapping, NamedTuple


KERNEL = "PS-ROOT-TRANSITION-KERNEL-1"
COMMAND = "/supernova-root-authorize v1"
COMMAND_PREFIX = COMMAND + " "
REPOSITORY_ID = 1338642578
OWNER_USER_ID = 222771578
MAX_LIFETIME_SECONDS = 30 * 60
MAX_AUTHORIZATION_LIFETIME = timedelta(seconds=MAX_LIFETIME_SECONDS)
BOUND_FIELDS = (
    "kernel",
    "repo_id",
    "owner_id",
    "pr",
    "base",
    "head",
    "tree",
    "changed_path_blob_manifest_sha256",
    "predecessor_epoch",
    "successor_epoch",
    "nonce",
    "expires",
)

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_POSITIVE_INTEGER = r"[1-9][0-9]*"
_EPOCH = r"(?:0|[1-9][0-9]*)"
_UTC_SECONDS = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
_COMMAND = re.compile(
    rf"{re.escape(COMMAND_PREFIX)}"
    rf"kernel=(?P<kernel>{re.escape(KERNEL)}) "
    rf"repo_id=(?P<repo_id>{_POSITIVE_INTEGER}) "
    rf"owner_id=(?P<owner_id>{_POSITIVE_INTEGER}) "
    rf"pr=(?P<pr>{_POSITIVE_INTEGER}) "
    r"base=(?P<base>[0-9a-f]{40}) "
    r"head=(?P<head>[0-9a-f]{40}) "
    r"tree=(?P<tree>[0-9a-f]{40}) "
    r"changed_path_blob_manifest_sha256=(?P<manifest>[0-9a-f]{64}) "
    rf"predecessor_epoch=(?P<predecessor_epoch>{_EPOCH}) "
    rf"successor_epoch=(?P<successor_epoch>{_EPOCH}) "
    r"nonce=(?P<nonce>[0-9a-f]{64}) "
    rf"expires=(?P<expires>{_UTC_SECONDS})"
)


class AuthorizationError(ValueError):
    """The supplied owner authorization is not exact and authoritative."""


class RootTransitionCommand(NamedTuple):
    kernel: str
    repo_id: int
    owner_id: int
    pr: int
    base: str
    head: str
    tree: str
    changed_path_blob_manifest_sha256: str
    predecessor_epoch: int
    successor_epoch: int
    nonce: str
    expires: str


class RootTransitionAuthorization(NamedTuple):
    comment_id: int
    html_url: str
    created_at: str
    expires_at: str
    nonce: str
    repository: str
    repo_id: int
    owner_id: int
    owner_login: str
    pr: int
    base: str
    head: str
    tree: str
    changed_path_blob_manifest_sha256: str
    predecessor_epoch: int
    successor_epoch: int


def contract() -> dict[str, Any]:
    """Return the frozen configuration projection for trusted census checks."""

    return {
        "schema_version": KERNEL,
        "helper": "scripts/root_transition_authorization.py",
        "command": COMMAND,
        "command_prefix": COMMAND_PREFIX,
        "repository_id": REPOSITORY_ID,
        "owner_user_id": OWNER_USER_ID,
        "max_lifetime_seconds": MAX_LIFETIME_SECONDS,
        "bound_fields": list(BOUND_FIELDS),
    }


def _fail(message: str) -> None:
    raise AuthorizationError(message)


def _exact_positive_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        _fail(name + " must be one exact positive integer")
    return value


def _exact_epoch(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _fail(name + " must be one exact nonnegative integer")
    return value


def _exact_hex(value: object, pattern: re.Pattern[str], name: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        _fail(name + " is not canonical lowercase hexadecimal")
    return value


def _utc_seconds(value: object, name: str) -> datetime:
    if not isinstance(value, str) or re.fullmatch(_UTC_SECONDS, value) is None:
        _fail(name + " is not canonical UTC seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise AuthorizationError(name + " is not a real UTC instant") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        _fail(name + " is not canonical UTC seconds")
    return parsed


def github_server_datetime(value: object) -> datetime:
    """Parse one exact IMF-fixdate GitHub HTTP Date value."""

    if not isinstance(value, str) or not value.endswith(" GMT"):
        _fail("GitHub server Date is absent or not IMF-fixdate")
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise AuthorizationError("GitHub server Date is invalid") from exc
    if parsed is None or parsed.tzinfo is None:
        _fail("GitHub server Date has no timezone")
    parsed = parsed.astimezone(timezone.utc)
    canonical = parsed.strftime("%a, %d %b %Y %H:%M:%S GMT")
    if canonical != value:
        _fail("GitHub server Date is not canonical IMF-fixdate")
    return parsed


def format_exact_command(command: RootTransitionCommand) -> str:
    """Format fields in the only admitted order; semantic checks are in parse."""

    if not isinstance(command, RootTransitionCommand):
        _fail("root transition command has the wrong value type")
    return (
        f"{COMMAND_PREFIX}kernel={command.kernel} repo_id={command.repo_id} "
        f"owner_id={command.owner_id} pr={command.pr} base={command.base} "
        f"head={command.head} tree={command.tree} "
        "changed_path_blob_manifest_sha256="
        f"{command.changed_path_blob_manifest_sha256} "
        f"predecessor_epoch={command.predecessor_epoch} "
        f"successor_epoch={command.successor_epoch} nonce={command.nonce} "
        f"expires={command.expires}"
    )


def parse_exact_command(body: object) -> RootTransitionCommand:
    """Parse the anchored no-extra-text owner command and its invariants."""

    if not isinstance(body, str):
        _fail("root transition command body is not text")
    match = _COMMAND.fullmatch(body)
    if match is None:
        _fail("root transition command is not exact")
    command = RootTransitionCommand(
        kernel=match.group("kernel"),
        repo_id=int(match.group("repo_id")),
        owner_id=int(match.group("owner_id")),
        pr=int(match.group("pr")),
        base=match.group("base"),
        head=match.group("head"),
        tree=match.group("tree"),
        changed_path_blob_manifest_sha256=match.group("manifest"),
        predecessor_epoch=int(match.group("predecessor_epoch")),
        successor_epoch=int(match.group("successor_epoch")),
        nonce=match.group("nonce"),
        expires=match.group("expires"),
    )
    if command.base == command.head:
        _fail("root transition base and head must differ")
    if command.successor_epoch != command.predecessor_epoch + 1:
        _fail("root transition must advance exactly one epoch")
    _utc_seconds(command.expires, "root transition expiry")
    return command


def _manifest_rows(
    changed_path_blobs: Mapping[str, str] | Iterable[tuple[str, str]],
) -> list[dict[str, str]]:
    if isinstance(changed_path_blobs, Mapping):
        supplied: Iterable[tuple[str, str]] = changed_path_blobs.items()
    elif isinstance(changed_path_blobs, (str, bytes)):
        _fail("changed path blob manifest is not a row collection")
    else:
        supplied = changed_path_blobs
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    try:
        for row in supplied:
            if not isinstance(row, (tuple, list)) or len(row) != 2:
                _fail("changed path blob manifest row is not one pair")
            path, blob = row
            if not isinstance(path, str) or not path:
                _fail("changed path is not nonempty text")
            if (
                path.startswith("/")
                or "\\" in path
                or posixpath.normpath(path) != path
                or ".." in path.split("/")
                or any(ord(character) < 32 or ord(character) == 127 for character in path)
            ):
                _fail("changed path is not canonical repository-relative POSIX text")
            if path in seen:
                _fail("changed path blob manifest contains a duplicate path")
            seen.add(path)
            rows.append((path, _exact_hex(blob, _HEX40, "changed path blob")))
    except AuthorizationError:
        raise
    except (TypeError, ValueError) as exc:
        raise AuthorizationError("changed path blob manifest is not iterable pairs") from exc
    if not rows:
        _fail("changed path blob manifest is empty")
    return [{"path": path, "blob": blob} for path, blob in sorted(rows)]


def canonical_changed_path_blob_manifest(
    changed_path_blobs: Mapping[str, str] | Iterable[tuple[str, str]],
) -> str:
    """Return the one UTF-8 JSON serialization used by the command digest."""

    value = {"changed_paths": _manifest_rows(changed_path_blobs)}
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_changed_path_blob_manifest_sha256(
    changed_path_blobs: Mapping[str, str] | Iterable[tuple[str, str]],
) -> str:
    payload = canonical_changed_path_blob_manifest(changed_path_blobs).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_exact_owner_authorization(
    comment: object,
    *,
    server_date: object,
    repository: str,
    repo_id: int,
    owner_id: int,
    owner_login: str,
    owner_type: str,
    pr: int,
    base: str,
    head: str,
    tree: str,
    changed_path_blob_manifest_sha256: str,
    predecessor_epoch: int,
    successor_epoch: int,
) -> RootTransitionAuthorization:
    """Validate one immutable API comment against every trusted binding."""

    if not isinstance(comment, Mapping):
        _fail("owner authorization comment is not an object")
    _exact_positive_integer(repo_id, "repository id")
    _exact_positive_integer(owner_id, "owner id")
    if repo_id != REPOSITORY_ID:
        _fail("repository id is not the frozen Supernova repository")
    if owner_id != OWNER_USER_ID:
        _fail("owner id is not the frozen Supernova owner")
    _exact_positive_integer(pr, "pull request number")
    _exact_hex(base, _HEX40, "expected base")
    _exact_hex(head, _HEX40, "expected head")
    _exact_hex(tree, _HEX40, "expected tree")
    _exact_hex(
        changed_path_blob_manifest_sha256,
        _HEX64,
        "expected changed path blob manifest digest",
    )
    _exact_epoch(predecessor_epoch, "predecessor epoch")
    _exact_epoch(successor_epoch, "successor epoch")
    if successor_epoch != predecessor_epoch + 1:
        _fail("expected epochs do not advance exactly once")
    if not isinstance(repository, str) or not repository or repository.count("/") != 1:
        _fail("repository identity is not exact owner/name text")
    if not isinstance(owner_login, str) or not owner_login:
        _fail("owner login is not exact text")
    if owner_type != "User":
        _fail("nominated owner type is not User")

    comment_id = _exact_positive_integer(comment.get("id"), "comment id")
    user = comment.get("user")
    if not isinstance(user, Mapping):
        _fail("comment user identity is absent")
    if (
        user.get("id") != owner_id
        or isinstance(user.get("id"), bool)
        or user.get("login") != owner_login
        or user.get("type") != owner_type
    ):
        _fail("comment author is not the exact nominated owner")
    if comment.get("author_association") != "OWNER":
        _fail("comment author association is not OWNER")
    if comment.get("performed_via_github_app") is not None:
        _fail("owner authorization was performed via a GitHub App")

    expected_api_url = f"https://api.github.com/repos/{repository}/issues/comments/{comment_id}"
    expected_issue_url = f"https://api.github.com/repos/{repository}/issues/{pr}"
    expected_html_url = f"https://github.com/{repository}/pull/{pr}#issuecomment-{comment_id}"
    if comment.get("url") != expected_api_url:
        _fail("comment API URL is not source-bound")
    if comment.get("issue_url") != expected_issue_url:
        _fail("comment issue URL is not pull-request-bound")
    if comment.get("html_url") != expected_html_url:
        _fail("comment HTML URL is not pull-request-bound")

    created_text = comment.get("created_at")
    updated_text = comment.get("updated_at")
    if created_text != updated_text:
        _fail("owner authorization comment was edited")
    created_at = _utc_seconds(created_text, "comment creation time")
    now = github_server_datetime(server_date)

    command = parse_exact_command(comment.get("body"))
    expected_bindings: tuple[tuple[str, object, object], ...] = (
        ("kernel", command.kernel, KERNEL),
        ("repository id", command.repo_id, repo_id),
        ("owner id", command.owner_id, owner_id),
        ("pull request", command.pr, pr),
        ("base", command.base, base),
        ("head", command.head, head),
        ("tree", command.tree, tree),
        (
            "changed path blob manifest digest",
            command.changed_path_blob_manifest_sha256,
            changed_path_blob_manifest_sha256,
        ),
        ("predecessor epoch", command.predecessor_epoch, predecessor_epoch),
        ("successor epoch", command.successor_epoch, successor_epoch),
    )
    for name, observed, expected in expected_bindings:
        if observed != expected:
            _fail("owner command " + name + " binding mismatch")

    expires_at = _utc_seconds(command.expires, "root transition expiry")
    lifetime = expires_at - created_at
    if lifetime <= timedelta(0) or lifetime > MAX_AUTHORIZATION_LIFETIME:
        _fail("owner authorization lifetime is outside (0, 30 minutes]")
    if now < created_at or now >= expires_at:
        _fail("owner authorization is not live at GitHub server time")

    return RootTransitionAuthorization(
        comment_id=comment_id,
        html_url=expected_html_url,
        created_at=created_text,
        expires_at=command.expires,
        nonce=command.nonce,
        repository=repository,
        repo_id=repo_id,
        owner_id=owner_id,
        owner_login=owner_login,
        pr=pr,
        base=base,
        head=head,
        tree=tree,
        changed_path_blob_manifest_sha256=changed_path_blob_manifest_sha256,
        predecessor_epoch=predecessor_epoch,
        successor_epoch=successor_epoch,
    )
