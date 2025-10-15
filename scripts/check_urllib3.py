#!/usr/bin/env python3
"""Comprobación rápida de urllib3 y la librería SSL para CI/local.
Sale con código 0 si urllib3 es 1.x, y código 2 si detecta urllib3 2.x (o superior).
"""
import sys
import ssl
import urllib3

def main():
    ver = urllib3.__version__
    print(f"urllib3 version: {ver}")
    print(f"ssl compiled with: {ssl.OPENSSL_VERSION}")
    try:
        major = int(ver.split('.')[0])
    except Exception:
        print("No se pudo parsear la versión de urllib3")
        return 3
    if major >= 2:
        print("ERROR: urllib3 v2 detected — incompatible con LibreSSL en este sistema")
        return 2
    print("OK: urllib3 1.x detected")
    return 0

if __name__ == '__main__':
    sys.exit(main())
