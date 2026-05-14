import logging
from typing import Any

from PyQt6.QtCore import QSettings

from asyncua import crypto, ua
from asyncua.sync import Client, SyncNode
from asyncua.tools import endpoint_to_strings


logger = logging.getLogger(__name__)


class UaClient:
    """
    OPC-Ua client specialized for the need of GUI client
    return exactly what GUI needs, no customization possible
    """

    def __init__(self) -> None:
        self.settings = QSettings()
        self.application_uri = "urn:freeopcua:client-gui"
        self.client: Client | None = None
        self._connected = False
        self._datachange_sub: Any = None
        self._event_sub: Any = None
        self._subs_dc: dict[ua.NodeId, Any] = {}
        self._subs_ev: dict[ua.NodeId, Any] = {}
        self.security_mode: str | None = None
        self.security_policy: str | None = None
        self.user_certificate_path: str | None = None
        self.user_private_key_path: str | None = None
        self.application_certificate_path: str | None = None
        self.application_private_key_path: str | None = None
        self.load_application_certificate_settings()

    def _reset(self) -> None:
        self.client = None
        self._connected = False
        self._datachange_sub = None
        self._event_sub = None
        self._subs_dc = {}
        self._subs_ev = {}

    @staticmethod
    def get_endpoints(uri: str) -> list[ua.EndpointDescription]:
        client = Client(uri, timeout=2)
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

        mysettings = self.settings.value("security_settings", None)
        if mysettings is None:
            return
        if uri in mysettings:
            mode, policy, cert, key = mysettings[uri]
            self.security_mode = mode
            self.security_policy = policy
            self.user_certificate_path = cert
            self.user_private_key_path = key

    def save_security_settings(self, uri: str) -> None:
        mysettings = self.settings.value("security_settings", None)
        if mysettings is None:
            mysettings = {}
        mysettings[uri] = [self.security_mode,
                           self.security_policy,
                           self.user_certificate_path,
                           self.user_private_key_path]
        self.settings.setValue("security_settings", mysettings)

    def load_application_certificate_settings(self) -> None:
        self.application_certificate_path = None
        self.application_private_key_path = None

        mysettings = self.settings.value("application_certificate_settings", None)
        if mysettings is None:
            return
        self.application_certificate_path = mysettings["application_certificate"]
        self.application_private_key_path = mysettings["application_private_key"]

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
        logger.info("Connecting to %s with parameters %s, %s, %s, %s", uri, self.security_mode, self.security_policy, self.user_certificate_path, self.user_private_key_path)
        self.client = Client(uri)
        self.client.application_uri = self.application_uri
        self.client.description = "FreeOpcUa Client GUI"

        if self.user_private_key_path:
            self.client.load_private_key(self.user_private_key_path)
        if self.user_certificate_path:
            self.client.load_client_certificate(self.user_certificate_path)

        if self.security_mode is not None and self.security_policy is not None:
            self.client.set_security(
                getattr(crypto.security_policies, 'SecurityPolicy' + self.security_policy),
                self.application_certificate_path,
                self.application_private_key_path,
                mode=getattr(ua.MessageSecurityMode, self.security_mode)
            )
        self.client.connect()
        self._connected = True
        try:
            self.client.load_data_type_definitions()
            self.client.load_enums()
            self.client.load_type_definitions()
        except Exception:
            logger.exception("Loading custom types failed (server may pre-date spec 1.04)")
        self.save_security_settings(uri)

    def disconnect(self) -> None:
        if self._connected:
            logger.info("Disconnecting from server")
            self._connected = False
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
