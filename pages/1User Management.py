from __future__ import annotations

import pandas as pd
import streamlit as st

from Utilities.auth import (
    AUTH_USER_KEY,
    build_invite_link,
    create_managed_user,
    create_password_setup_invite,
    create_invite,
    delete_managed_user,
    email_delivery_configured,
    get_invites,
    get_managed_users,
    get_password_setup_invite,
    get_user_directory,
    require_login,
    revoke_invite,
    set_password,
    send_invite_email,
    update_managed_user_settings,
)
from Utilities.mobile import inject_mobile_css


st.set_page_config(
    page_title="User Management",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_login(["admin"])
inject_mobile_css()

st.title("👥 User Management")
st.markdown("Manage users, roles, and registration invites.")
st.markdown("---")


ROLE_OPTIONS = ["admin", "financial analyst", "validator"]
current_admin = str(st.session_state.get(AUTH_USER_KEY, "admin"))


def _safe_multiselect_key(prefix: str, username: str) -> str:
    return f"{prefix}_{username.lower().replace(' ', '_')}"


def _show_user_directory() -> None:
    st.subheader("Users", divider="blue")
    users = get_user_directory()
    if not users:
        st.info("No users are configured.")
        return

    directory_rows = []
    for user in users:
        directory_rows.append(
            {
                "Username": user.get("username"),
                "Email": user.get("email") or "",
                "Roles": ", ".join(user.get("roles", [])),
                "Status": "Active" if user.get("is_active", True) else "Inactive",
                "Password Change Required": "Yes" if user.get("must_change_password", False) else "No",
                "Source": user.get("source", "managed"),
            }
        )
    st.dataframe(pd.DataFrame(directory_rows),
                 use_container_width=True, hide_index=True)

    managed_users = get_managed_users()
    if not managed_users:
        st.caption("Managed users will appear here after invite registration.")
        return

    st.markdown("### Managed User Controls")
    for user in managed_users:
        with st.expander(f"{user['username']} ({', '.join(user.get('roles', []))})", expanded=False):
            updated_roles = st.multiselect(
                "Roles",
                ROLE_OPTIONS,
                default=user.get("roles", []),
                key=_safe_multiselect_key("roles", user["username"]),
            )
            is_active = st.checkbox(
                "Active",
                value=bool(user.get("is_active", True)),
                key=_safe_multiselect_key("active", user["username"]),
            )
            must_change_password = st.checkbox(
                "Require password change on next login",
                value=bool(user.get("must_change_password", False)),
                key=_safe_multiselect_key("must_change", user["username"]),
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save user", key=_safe_multiselect_key("save", user["username"]), use_container_width=True):
                    try:
                        update_managed_user_settings(
                            user["username"], updated_roles, is_active, must_change_password)
                        st.success(f"Updated {user['username']}.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            with col2:
                if st.button("Delete user", key=_safe_multiselect_key("delete", user["username"]), use_container_width=True):
                    try:
                        delete_managed_user(user["username"])
                        st.success(f"Deleted {user['username']}.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            setup_invite = get_password_setup_invite(user["username"])
            if setup_invite:
                st.caption("Password setup link")
                st.code(build_invite_link(setup_invite["token"]))
            if st.button("Generate password setup link", key=_safe_multiselect_key("setup_link", user["username"]), use_container_width=True):
                try:
                    setup_invite = create_password_setup_invite(
                        user["username"], current_admin)
                    st.success("Password setup link generated.")
                    st.code(build_invite_link(setup_invite["token"]))
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            reset_password = st.text_input(
                "Set temporary password",
                type="password",
                key=_safe_multiselect_key("temp_password", user["username"]),
            )
            if st.button("Reset password", key=_safe_multiselect_key("reset_password", user["username"]), use_container_width=True):
                try:
                    set_password(user["username"], reset_password,
                                 force_change_next_login=True)
                    st.success(
                        f"Temporary password set for {user['username']}. They will be forced to change it at next login.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))


def _show_invite_creation() -> None:
    st.subheader("Manual Invite Links", divider="green")
    email_enabled = email_delivery_configured()
    st.caption(
        "Create a registration link manually, copy it, and send it outside the app. "
        "The invited user will choose their own username and password from that link."
    )
    if not email_enabled:
        st.info(
            "SMTP is not configured. You can still create invites and copy the registration link manually. "
            "Set AVISK_SMTP_HOST, AVISK_SMTP_PORT, AVISK_SMTP_USERNAME, AVISK_SMTP_FROM_EMAIL, "
            "and either AVISK_SMTP_PASSWORD or AVISK_SMTP_PASSWORD_SECRET to send emails from the app."
        )

    with st.form("create_user_invite"):
        email = st.text_input("Email address")
        roles = st.multiselect("Roles", ROLE_OPTIONS, default=["validator"])
        expires_hours = st.number_input(
            "Invite expires in hours", min_value=1, max_value=720, value=72, step=1)
        send_email_now = st.checkbox(
            "Send invite email now", value=email_enabled, disabled=not email_enabled)
        submitted = st.form_submit_button(
            "Create invite", use_container_width=True)

    if not submitted:
        return

    try:
        invite = create_invite(email, roles, current_admin, int(expires_hours))
    except ValueError as exc:
        st.error(str(exc))
        return

    invite_link = build_invite_link(invite["token"])
    st.success(f"Invite created for {invite['email']}.")
    st.code(invite_link)

    if send_email_now:
        sent, result = send_invite_email(invite["invite_id"])
        if sent:
            st.success("Invite email sent.")
        else:
            st.warning(f"Invite created but email failed: {result}")


def _show_manual_user_creation() -> None:
    st.subheader("Create Users Manually", divider="violet")
    st.caption(
        "Create a user record and generate a password setup link to share. "
        "The user will set their own password from that link."
    )

    username = st.text_input("Username", key="manual_user_username")
    email = st.text_input("Email address", key="manual_user_email")
    roles = st.multiselect("Roles", ROLE_OPTIONS, default=[
                           "validator"], key="manual_user_roles")
    is_active = st.checkbox("Active", value=True, key="manual_user_active")

    submitted = st.button(
        "Create user", use_container_width=True, key="manual_user_create_submit")

    if not submitted:
        return

    try:
        user = create_managed_user(
            username=username,
            email=email,
            roles=roles,
            is_active=is_active,
            must_change_password=False,
        )
        setup_invite = create_password_setup_invite(
            user["username"], current_admin)
    except ValueError as exc:
        st.error(str(exc))
        return

    st.success(f"User {user['username']} created.")
    st.code(build_invite_link(setup_invite["token"]))


def _show_invite_directory() -> None:
    st.subheader("Pending and Past Invites", divider="orange")
    invites = get_invites()
    if not invites:
        st.caption("No invites have been created yet.")
        return

    for invite in invites:
        title = f"{invite['email']} • {invite['status']} • {', '.join(invite.get('roles', []))}"
        with st.expander(title, expanded=False):
            st.write(f"Invite link: {build_invite_link(invite['token'])}")
            st.write(f"Created: {invite.get('created_at') or 'n/a'}")
            st.write(f"Expires: {invite.get('expires_at') or 'n/a'}")
            st.write(f"Invited by: {invite.get('invited_by') or 'n/a'}")
            if invite.get("registered_username"):
                st.write(
                    f"Registered username: {invite['registered_username']}")
            if invite.get("last_email_error"):
                st.warning(f"Last email error: {invite['last_email_error']}")

            col1, col2 = st.columns(2)
            with col1:
                resend_disabled = invite.get("status") != "pending"
                if st.button("Send email", key=f"send_{invite['invite_id']}", use_container_width=True, disabled=resend_disabled):
                    sent, result = send_invite_email(invite["invite_id"])
                    if sent:
                        st.success("Invite email sent.")
                        st.rerun()
                    else:
                        st.error(result)
            with col2:
                revoke_disabled = invite.get("status") != "pending"
                if st.button("Revoke invite", key=f"revoke_{invite['invite_id']}", use_container_width=True, disabled=revoke_disabled):
                    revoke_invite(invite["invite_id"])
                    st.success("Invite revoked.")
                    st.rerun()


_show_user_directory()
st.markdown("---")
_show_manual_user_creation()
st.markdown("---")
_show_invite_creation()
st.markdown("---")
_show_invite_directory()
