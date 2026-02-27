"""
Admin Panel — Service Management

Provides start / stop / restart controls for the avisk-core-services systemd
service, plus a live log tail, all from inside the Streamlit frontend.

Sudoers requirement (already configured if vm-deploy.sh was used):
  avisk ALL=(ALL) NOPASSWD: /bin/systemctl start avisk-core-services, \
                             /bin/systemctl stop avisk-core-services,  \
                             /bin/systemctl restart avisk-core-services,\
                             /bin/systemctl status avisk-core-services
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path
import sys

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

SERVICE = "avisk-core-services"
SUDO_SYSTEMCTL = ["sudo", "systemctl"]

st.set_page_config(
    page_title="Admin — Service Management",
    page_icon="⚙️",
    layout="wide",
)

from Utilities.mobile import inject_mobile_css  # noqa: E402
inject_mobile_css()

st.title("⚙️ Admin — Service Management")
st.markdown(f"Control and monitor the **`{SERVICE}`** systemd service.")

# ── helpers ────────────────────────────────────────────────────────────────────


def _run(args: list[str], timeout: int = 10) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as exc:
        return 1, "", str(exc)


def get_status() -> dict:
    """Return a dict with keys: active, sub, description, raw."""
    rc, out, _ = _run(SUDO_SYSTEMCTL + ["status", SERVICE, "--no-pager", "-l"])
    active = "unknown"
    sub = ""
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Active:"):
            parts = line.split(":", 1)[1].strip()
            # e.g. "active (running) since ..."
            # "active" / "inactive" / "failed"
            active = parts.split("(")[0].strip()
            if "(" in parts:
                # "running" / "dead" / "exited"
                sub = parts.split("(")[1].split(")")[0]
            break
    return {"active": active, "sub": sub, "raw": out, "rc": rc}


def _deferred_action(action: str):
    """
    Run `systemctl <action>` in a detached subprocess so the page can render
    a status message before the service is killed (important for 'stop').
    """
    script = f"sleep 1 && sudo systemctl {action} {SERVICE}"
    subprocess.Popen(
        ["bash", "-c", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def tail_journal(lines: int = 60) -> str:
    """Return the last N lines of the service journal."""
    _, out, err = _run(
        ["sudo", "journalctl", "-u", SERVICE,
            f"-n{lines}", "--no-pager", "-l"],
        timeout=15,
    )
    return out or err


# ── status card ────────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("📡 Current Status")

status_placeholder = st.empty()
refreshed_at = st.caption("")


def render_status():
    s = get_status()
    is_running = s["active"] == "active" and s["sub"] == "running"
    is_failed = s["active"] == "failed"

    with status_placeholder.container():
        col_icon, col_info = st.columns([1, 5])
        with col_icon:
            if is_running:
                st.success("🟢 Running")
            elif is_failed:
                st.error("🔴 Failed")
            else:
                st.warning("🟡 Stopped")
        with col_info:
            st.markdown(
                f"**State:** `{s['active']}` &nbsp;·&nbsp; **Sub-state:** `{s['sub']}`"
            )
            with st.expander("Raw systemctl output", expanded=False):
                st.code(s["raw"] or "(no output)", language="bash")

    refreshed_at.caption(
        f"Last refreshed: {datetime.now().strftime('%H:%M:%S')}")
    return s


current = render_status()

if st.button("🔄 Refresh Status"):
    current = render_status()

# ── action buttons ─────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("🎛️ Service Controls")

is_running = current["active"] == "active" and current["sub"] == "running"

col1, col2, col3 = st.columns(3)

with col1:
    restart_clicked = st.button(
        "🔁 Restart",
        use_container_width=True,
        type="primary",
        help="Gracefully restart the service (apply new code without manual SSH)",
    )

with col2:
    stop_clicked = st.button(
        "🛑 Stop",
        use_container_width=True,
        disabled=not is_running,
        help="Stop the service. ⚠️ This will take the UI offline.",
    )

with col3:
    start_clicked = st.button(
        "▶️ Start",
        use_container_width=True,
        disabled=is_running,
        help="Start the service if it is currently stopped.",
    )

# Confirmation gate for destructive actions
if "confirm_stop" not in st.session_state:
    st.session_state.confirm_stop = False
if "confirm_restart" not in st.session_state:
    st.session_state.confirm_restart = False

if stop_clicked:
    st.session_state.confirm_stop = True
    st.session_state.confirm_restart = False

if restart_clicked:
    st.session_state.confirm_restart = True
    st.session_state.confirm_stop = False

# ── confirmation dialogs ───────────────────────────────────────────────────────

if st.session_state.confirm_stop:
    st.warning(
        "⚠️ **Stopping the service will take this UI offline.**  "
        "You will need to SSH into the VM to start it again, or click **Start** before closing this window."
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Yes, stop it", type="primary", use_container_width=True):
            st.session_state.confirm_stop = False
            st.info("🛑 Sending stop signal — the page will go offline in a moment...")
            _deferred_action("stop")
            time.sleep(2)
            st.rerun()
    with c2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.confirm_stop = False
            st.rerun()

if st.session_state.confirm_restart:
    st.warning(
        "🔁 **Restarting the service will briefly interrupt the UI** (a few seconds).  "
        "The page will reload automatically once the service is back up."
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Yes, restart it", type="primary", use_container_width=True):
            st.session_state.confirm_restart = False
            st.info(
                "🔁 Sending restart signal — the service will reload in a few seconds...")
            _deferred_action("restart")
            time.sleep(3)
            st.rerun()
    with c2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.confirm_restart = False
            st.rerun()

if start_clicked:
    with st.spinner("Starting service..."):
        rc, out, err = _run(SUDO_SYSTEMCTL + ["start", SERVICE])
    if rc == 0:
        st.success("▶️ Service started successfully.")
    else:
        st.error(f"Failed to start service:\n```\n{err or out}\n```")
    time.sleep(1)
    st.rerun()

# ── live log tail ──────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("📋 Service Logs")

log_lines = st.slider("Lines to show", min_value=20,
                      max_value=200, value=60, step=20)

col_log, col_refresh = st.columns([5, 1])
with col_refresh:
    auto_refresh = st.checkbox("Auto-refresh (10 s)", value=False)

logs = tail_journal(log_lines)
log_box = st.code(logs or "(no logs)", language="bash")

if auto_refresh:
    time.sleep(10)
    st.rerun()
