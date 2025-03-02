import socket

class WebServer:
    def __init__(self, wifi_manager):
        self.wifi_manager = wifi_manager
        self.addr = socket.getaddrinfo('192.168.4.1', 80)[0][-1]

    async def handle_request(self, conn):
        """Обрабатывает HTTP-запросы."""
        request = conn.recv(1024).decode()
        if "GET / " in request:
            networks = self.wifi_manager.scan_networks()
            response = self.render_form(networks)
        elif "POST /connect" in request:
            body = request.split("\r\n\r\n")[1]
            params = dict(pair.split("=") for pair in body.split("&"))
            ssid = params.get("ssid", "")
            password = params.get("password", "")
            if self.wifi_manager.connect(ssid, password):
                self.wifi_manager.save_config(ssid, password)
                response = self.render_success_page()
            else:
                response = self.render_error_page()
        else:
            response = self.render_not_found_page()
        conn.send(response)
        conn.close()

    def redirect_to_user_network(self, ip_address):
        """Перенаправляет пользователя на IP-адрес в пользовательской сети."""
        redirect_html = f"""
            <html>
            <head>
                <meta http-equiv="refresh" content="0; url=http://{ip_address}/info">
            </head>
            <body>
                <p>Redirecting to <a href="http://{ip_address}/info">http://{ip_address}/info</a>...</p>
            </body>
            </html>
        """
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(redirect_html)}\r\n"
            "\r\n"
            f"{redirect_html}"
        )
        return response.encode()

    def render_form(self, networks):
        """Отрисовывает HTML-форму с красивыми стилями и кнопкой 'Show/Hide'."""
        options = "".join(f"<option value='{network}'>{network}</option>" for network in networks)
        html_content = f"""
            <html>
            <head>
                <title>Wi-Fi Setup</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background-color: #f4f4f9;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }}
                    .container {{
                        background: white;
                        padding: 2rem;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        width: 300px;
                        text-align: center;
                    }}
                    h1 {{
                        font-size: 1.5rem;
                        margin-bottom: 1.5rem;
                        color: #333;
                    }}
                    select, input[type="password"], input[type="text"], input[type="submit"] {{
                        width: 100%;
                        padding: 0.5rem;
                        margin-bottom: 1rem;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        font-size: 1rem;
                    }}
                    input[type="submit"] {{
                        background-color: #007bff;
                        color: white;
                        border: none;
                        cursor: pointer;
                    }}
                    input[type="submit"]:hover {{
                        background-color: #0056b3;
                    }}
                    .password-container {{
                        position: relative;
                        width: 100%;
                    }}
                    .toggle-password {{
                        position: absolute;
                        right: 10px;
                        top: 50%;
                        transform: translateY(-50%);
                        cursor: pointer;
                        color: #007bff;
                        background: none;
                        border: none;
                        font-size: 0.9rem;
                    }}
                    .popup {{
                        display: none;
                        position: fixed;
                        top: 20px;
                        left: 50%;
                        transform: translateX(-50%);
                        background-color: #ff4444;
                        color: white;
                        padding: 10px 20px;
                        border-radius: 5px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Wi-Fi Configuration</h1>
                    <form action="/connect" method="post">
                        <select name="ssid">
                            {options}
                        </select><br>
                        <div class="password-container">
                            <input type="password" name="password" id="password" placeholder="Password"><br>
                            <button type="button" class="toggle-password" id="toggle-password" onclick="togglePasswordVisibility()">Show</button>
                        </div>
                        <input type="submit" value="Connect">
                    </form>
                </div>
                <div id="popup" class="popup">Failed to connect. Please try again.</div>
                <script>
                    function togglePasswordVisibility() {{
                        const passwordInput = document.getElementById('password');
                        const toggleButton = document.getElementById('toggle-password');
                        if (passwordInput.type === 'password') {{
                            passwordInput.type = 'text';
                            toggleButton.textContent = 'Hide';
                        }} else {{
                            passwordInput.type = 'password';
                            toggleButton.textContent = 'Show';
                        }}
                    }}

                    function showPopup() {{
                        document.getElementById('popup').style.display = 'block';
                        setTimeout(() => {{
                            document.getElementById('popup').style.display = 'none';
                        }}, 3000);
                    }}
                </script>
            </body>
            </html>
        """
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(html_content)}\r\n"
            "\r\n"
            f"{html_content}"
        )
        return response.encode()

    def render_success_page(self):
        """Отрисовывает страницу успешного подключения."""
        html_content = """
            <html>
            <head>
                <title>Success</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #f4f4f9;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .container {
                        background: white;
                        padding: 2rem;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        width: 300px;
                        text-align: center;
                    }
                    h1 {
                        font-size: 1.5rem;
                        margin-bottom: 1.5rem;
                        color: #333;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Connected!</h1>
                    <p>Redirecting to device info...</p>
                </div>
                <script>
                    setTimeout(() => {
                        window.location.href = "/info";
                    }, 2000);
                </script>
            </body>
            </html>
        """
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(html_content)}\r\n"
            "\r\n"
            f"{html_content}"
        )
        return response.encode()

    def render_error_page(self):
        """Отрисовывает страницу ошибки подключения."""
        html_content = """
            <html>
            <head>
                <title>Error</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #f4f4f9;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .container {
                        background: white;
                        padding: 2rem;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        width: 300px;
                        text-align: center;
                    }
                    h1 {
                        font-size: 1.5rem;
                        margin-bottom: 1.5rem;
                        color: #333;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Failed to connect</h1>
                    <p>Please check your SSID and password.</p>
                    <a href="/">Try again</a>
                </div>
            </body>
            </html>
        """
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(html_content)}\r\n"
            "\r\n"
            f"{html_content}"
        )
        return response.encode()

    def render_not_found_page(self):
        """Отрисовывает страницу 404."""
        html_content = """
            <html>
            <head>
                <title>404 Not Found</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #f4f4f9;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .container {
                        background: white;
                        padding: 2rem;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        width: 300px;
                        text-align: center;
                    }
                    h1 {
                        font-size: 1.5rem;
                        margin-bottom: 1.5rem;
                        color: #333;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>404 Not Found</h1>
                    <p>The page you requested does not exist.</p>
                    <a href="/">Go back</a>
                </div>
            </body>
            </html>
        """
        response = (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(html_content)}\r\n"
            "\r\n"
            f"{html_content}"
        )
        return response.encode()

    async def start(self):
        """Запускает веб-сервер."""
        s = socket.socket()
        s.bind(self.addr)
        s.listen(1)
        print("Web server started at http://192.168.4.1")
        while True:
            conn, addr = s.accept()
            await self.handle_request(conn)