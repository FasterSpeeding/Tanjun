# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020-2021, Faster Speeding
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# pyright: reportIncompatibleMethodOverride=none
# pyright: reportUnknownMemberType=none
# This leads to too many false-positives around mocks.

import base64
import importlib
import pathlib
import random
import tempfile
import textwrap
from unittest import mock

import pytest

import tanjun


class TestClient:
    def test_load_modules_with_system_path(self):
        class MockClient(tanjun.Client):
            add_component = mock.Mock()

            add_client_callback = mock.Mock()

        client = MockClient(mock.AsyncMock())

        # A try, finally is used to delete the file rather than relying on delete=True behaviour
        # as on Windows the file cannot be accessed by other processes if delete is True.
        file = tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False)
        path = pathlib.Path(file.name)
        try:
            with file:
                file.write(
                    textwrap.dedent(
                        """
                        import tanjun

                        foo = 123
                        bar = object()

                        @tanjun.as_loader
                        def load_module(client: tanjun.abc.Client) -> None:
                            assert isinstance(client, tanjun.Client)
                            client.add_component(123)
                            client.add_client_callback(4312)
                    """
                    )
                )
                file.flush()

            client.load_modules(path)

            client.add_component.assert_called_once_with(123)
            client.add_client_callback.assert_called_once_with(4312)

        finally:
            path.unlink(missing_ok=False)

    def test_load_modules_with_system_path_for_unknown_path(self):
        class MockClient(tanjun.Client):
            add_component = mock.Mock()
            add_client_callback = mock.Mock()

        client = MockClient(mock.AsyncMock())
        random_path = pathlib.Path(base64.urlsafe_b64encode(random.randbytes(64)).decode())

        with pytest.raises(RuntimeError):
            client.load_modules(random_path)

    def test_load_modules_with_python_module_path(self):
        client = tanjun.Client(mock.AsyncMock())

        mock_module = mock.Mock(object=123, foo="ok", loader=mock.Mock(tanjun.clients._LoadableDescriptor), no=object())

        with mock.patch.object(importlib, "import_module", return_value=mock_module) as import_module:
            client.load_modules("okokok.no.u")

            import_module.assert_called_once_with("okokok.no.u")

        mock_module.loader.assert_called_once_with(client)
