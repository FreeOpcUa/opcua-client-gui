import logging
from pathlib import Path
from typing import Any, Callable, Literal

from PyQt6.QtCore import QObject, QSettings, QStandardPaths, pyqtSignal

from asyncua import crypto, ua
from asyncua.client.ua_client import UaClientState
from asyncua.sync import Client, SyncNode, ThreadLoop
from asyncua.tools import endpoint_to_strings


logger = logging.getLogger(__name__)

AuthMode = Literal["anonymous", "username", "certificate"]


class UaClient(QObject):
    """
    OPC-Ua client specialized for the need of GUI client
    return exactly what GUI needs, no customization possible
    """

    # Forwarded from asyncua's connection state. Value is a UaClientState string
    # (e.g. "connected", "reconnecting", "disconnected"). Emitted from the
    # asyncua thread, so connect with QueuedConnection.
    connection_state_changed = pyqtSignal(str)

    def __init__(self) -> None:
        QObject.__init__(self)
        self.settings = QSettings()
        self.application_uri = "urn:freeopcua:client-gui"
        # One ThreadLoop is shared across every Client we open. sync.Client
        # owns and stops its threadloop on disconnect() when it created it,
        # which would tear down the asyncio loop our session lives on; passing
        # our own tloop keeps it alive across connect/disconnect cycles.
        self._tloop = ThreadLoop()
        self._tloop.start()
        self.client: Client | None = None
        self._connected = False
        self._datachange_sub: Any = None
        self._event_sub: Any = None
        self._subs_dc: dict[ua.NodeId, Any] = {}
        self._subs_ev: dict[ua.NodeId, Any] = {}
        self._unsubscribe_state: Callable[[], None] | None = None
        self.security_mode: str | None = None
        self.security_policy: str | None = None
        self.user_certificate_path: str | None = None
        self.user_private_key_path: str | None = None
        self.application_certificate_path: str | None = None
        self.application_private_key_path: str | None = None
        self.auth_mode: AuthMode = "anonymous"
        self.username: str | None = None
        self.password: str | None = None
        self.endpoint_url: str | None = None
        self.load_application_certificate_settings()

    def shutdown(self) -> None:
        """Tear down the shared ThreadLoop. Call once on application exit."""
        try:
            self._tloop.stop()
        except Exception:
            logger.exception("Failed to stop ThreadLoop")

    def _reset(self) -> None:
        if self._unsubscribe_state is not None:
            try:
                self._unsubscribe_state()
            except Exception:
                logger.exception("Failed to unsubscribe from state listener")
            self._unsubscribe_state = None
        self.client = None
        self._connected = False
        self._datachange_sub = None
        self._event_sub = None
        self._subs_dc = {}
        self._subs_ev = {}

    def get_endpoints(self, uri: str) -> list[ua.EndpointDescription]:
        client = Client(uri, timeout=2, tloop=self._tloop)
        edps = client.connect_and_get_server_endpoints()
        for i, ep in enumerate(edps, start=1):
            logger.info('Endpoint %s:', i)
            for (n, v) in endpoint_to_strings(ep):
                logger.info('  %s: %s', n, v)
            logger.info('')
        return edps

    def load_security_settings(self, uri: str) -> None:
        self.security_mode = None
        self.security_policy = None
        self.user_certificate_path = None
        self.user_private_key_path = None
        self.auth_mode = "anonymous"
        self.username = None
        self.endpoint_url = None

        mysettings = self.settings.value("security_settings", None)
        if mysettings is None or uri not in mysettings:
            return
        entry = mysettings[uri]
        if isinstance(entry, list):
            mode, policy, cert, key = entry
            self.security_mode = mode
            self.security_policy = policy
            self.user_certificate_path = cert
            self.user_private_key_path = key
            return
        self.security_mode = entry.get("mode")
        self.security_policy = entry.get("policy")
        self.user_certificate_path = entry.get("user_certificate")
        self.user_private_key_path = entry.get("user_private_key")
        self.auth_mode = entry.get("auth_mode", "anonymous")
        self.username = entry.get("username")
        self.endpoint_url = entry.get("endpoint_url")

    def save_security_settings(self, uri: str) -> None:
        mysettings = self.settings.value("security_settings", None)
        if mysettings is None:
            mysettings = {}
        mysettings[uri] = {
            "mode": self.security_mode,
            "policy": self.security_policy,
            "user_certificate": self.user_certificate_path,
            "user_private_key": self.user_private_key_path,
            "auth_mode": self.auth_mode,
            "username": self.username,
            "endpoint_url": self.endpoint_url,
        }
        self.settings.setValue("security_settings", mysettings)

    def load_application_certificate_settings(self) -> None:
        self.application_certificate_path = None
        self.application_private_key_path = None

        mysettings = self.settings.value("application_certificate_settings", None)
        if mysettings is None:
            return
        self.application_certificate_path = mysettings["application_certificate"]
        self.application_private_key_path = mysettings["application_private_key"]

    def generate_application_certificate(self) -> tuple[str, str]:
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        pki_dir = (Path(base) if base else Path.home() / ".freeopcua") / "pki"
        key_file = pki_dir / "own_private_key.pem"
        cert_file = pki_dir / "own_cert.der"
        client = Client("opc.tcp://localhost:4840", tloop=self._tloop)
        client.application_uri = self.application_uri
        cert, key = client.setup_self_signed_certificate(key_file=key_file, cert_file=cert_file)
        return str(cert), str(key)

    def save_application_certificate_settings(self) -> None:
        mysettings = self.settings.value("application_certificate_settings", None)
        if mysettings is None:
            mysettings = {}
        mysettings["application_certificate"] = self.application_certificate_path
        mysettings["application_private_key"] = self.application_private_key_path
        self.settings.setValue("application_certificate_settings", mysettings)

    def get_node(self, nodeid: ua.NodeId | str) -> SyncNode:
        assert self.client is not None
        return self.client.get_node(nodeid)

    def connect(self, uri: str) -> None:
        self.disconnect()
        logger.info("Connecting to %s with parameters %s, %s, %s, %s, %s", uri, self.auth_mode, self.security_mode, self.security_policy, self.user_certificate_path, self.user_private_key_path)
        self.client = Client(uri, tloop=self._tloop)
        self.client.application_uri = self.application_uri
        self.client.description = "FreeOpcUa Client GUI"

        if self.auth_mode == "username":
            if self.username:
                self.client.set_user(self.username)
            if self.password:
                self.client.set_password(self.password)
        elif self.auth_mode == "certificate":
            # asyncua picks the certificate identity token only when no username is set
            # and a user certificate is loaded, so these stay scoped to this mode.
            if self.user_private_key_path:
                self.client.load_private_key(self.user_private_key_path)
            if self.user_certificate_path:
                self.client.load_client_certificate(self.user_certificate_path)

        if self.security_mode is not None and self.security_policy is not None:
            if not (self.application_certificate_path and self.application_private_key_path):
                self.application_certificate_path, self.application_private_key_path = (
                    self.generate_application_certificate()
                )
                self.save_application_certificate_settings()
            # Endpoint policy URIs spell Aes policies with underscores
            # (Aes256_Sha256_RsaPss); the asyncua class name omits them.
            policy_class = 'SecurityPolicy' + self.security_policy.replace('_', '')
            self.client.set_security(
                getattr(crypto.security_policies, policy_class),
                self.application_certificate_path,
                self.application_private_key_path,
                mode=getattr(ua.MessageSecurityMode, self.security_mode)
            )
        self.client.connect(auto_reconnect=True)
        self._connected = True
        self._install_state_listener()
        try:
            self.client.load_data_type_definitions()
            self.client.load_enums()
            self.client.load_type_definitions()
        except Exception:
            logger.exception("Loading custom types failed (server may pre-date spec 1.04)")
        self.save_security_settings(uri)

    def _install_state_listener(self) -> None:
        """Forward asyncua state transitions to the Qt signal.

        The listener is invoked synchronously on the asyncua thread; we only
        emit a Qt signal so the slot runs on the GUI thread (the connection
        site uses QueuedConnection).
        """
        assert self.client is not None
        uaclient = self.client.aio_obj.uaclient
        self._unsubscribe_state = uaclient._add_state_listener(self._on_state_change)

    def _on_state_change(self, state: UaClientState) -> None:
        self.connection_state_changed.emit(state.value)

    def disconnect(self) -> None:
        if self._connected:
            logger.info("Disconnecting from server")
            self._connected = False
            # Unhook the state listener first: the asyncua disconnect()
            # will walk through DISCONNECTING/DISCONNECTED, but those are
            # part of the user-initiated teardown — we don't want the
            # GUI to flash an "auto-reconnect in progress" banner.
            if self._unsubscribe_state is not None:
                try:
                    self._unsubscribe_state()
                except Exception:
                    logger.exception("Failed to unsubscribe from state listener")
                self._unsubscribe_state = None
            try:
                assert self.client is not None
                self.client.disconnect()
            finally:
                self._reset()

    def subscribe_datachange(self, node: SyncNode, handler: Any) -> Any:
        assert self.client is not None
        if not self._datachange_sub:
            self._datachange_sub = self.client.create_subscription(500, handler)
        handle = self._datachange_sub.subscribe_data_change(node)
        self._subs_dc[node.nodeid] = handle
        return handle

    def unsubscribe_datachange(self, node: SyncNode) -> None:
        self._datachange_sub.unsubscribe(self._subs_dc[node.nodeid])

    def subscribe_events(self, node: SyncNode, handler: Any) -> Any:
        assert self.client is not None
        if not self._event_sub:
            self._event_sub = self.client.create_subscription(500, handler)
        handle = self._event_sub.subscribe_events(node)
        self._subs_ev[node.nodeid] = handle
        return handle

    def unsubscribe_events(self, node: SyncNode) -> None:
        self._event_sub.unsubscribe(self._subs_ev[node.nodeid])

    def get_node_attrs(self, node: SyncNode | ua.NodeId | str) -> tuple[SyncNode, list[str]]:
        if not isinstance(node, SyncNode):
            assert self.client is not None
            node = self.client.get_node(node)
        attrs = node.read_attributes([ua.AttributeIds.DisplayName, ua.AttributeIds.BrowseName, ua.AttributeIds.NodeId])
        return node, [attr.Value.Value.to_string() for attr in attrs]

    @staticmethod
    def get_children(node: SyncNode) -> list[ua.ReferenceDescription]:
        descs = node.get_children_descriptions()
        descs.sort(key=lambda x: x.BrowseName)
        return descs
