from django.db import models
import socket
import os


class Printer(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Exact Windows printer name, e.g. POS-90 or POS-80")
    display_name = models.CharField(max_length=150, blank=True, help_text="Friendly label shown in POS Checkout")
    server_ip = models.CharField(max_length=255, default="127.0.0.1", help_text="IP or hostname running the print server (127.0.0.1 for local host)")
    server_port = models.PositiveIntegerField(default=9101, help_text="Print server TCP port (default 9101)")
    enabled = models.BooleanField(default=True, help_text="Enable or disable printer")
    is_paused = models.BooleanField(default=False, help_text="Temporarily paused printer")
    is_default = models.BooleanField(default=False, help_text="Primary default POS printer")
    paper_width = models.CharField(max_length=10, default="80mm", choices=[("80mm", "80mm (Standard)"), ("58mm", "58mm (Compact)")])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "name"]
        verbose_name = "Thermal Printer"
        verbose_name_plural = "Thermal Printers"

    def __str__(self):
        return self.display_name or self.name

    def save(self, *args, **kwargs):
        """Only one printer can be the default printer."""
        if self.is_default:
            Printer.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def get_resolved_ip(self):
        """Resolve the configured print-server address (supports host.docker.internal)."""
        host = str(self.server_ip).strip()
        if not host or host == "0.0.0.0":
            host = "127.0.0.1"

        is_docker = os.path.exists("/.dockerenv") or os.environ.get("IN_DOCKER") == "1"

        # If inside Docker and pointing to loopback, route to host.docker.internal
        if is_docker and host.lower() in ("127.0.0.1", "localhost", "0.0.0.0"):
            host = "host.docker.internal"

        if host.lower() == "host.docker.internal":
            if is_docker:
                try:
                    return socket.gethostbyname("host.docker.internal")
                except socket.gaierror:
                    for fallback in ("172.17.0.1", "172.18.0.1", "10.0.75.1"):
                        try:
                            socket.inet_aton(fallback)
                            return fallback
                        except socket.error:
                            continue
                return host
            return "127.0.0.1"

        try:
            socket.inet_aton(host)
            return host
        except socket.error:
            pass

        try:
            return socket.gethostbyname(host)
        except socket.gaierror:
            return host
