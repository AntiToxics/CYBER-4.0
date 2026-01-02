"""
 Name: "Server.py"
 Author: Gilad Elran
 Purpose: Provides a Client-Server connection with protocol HTTP/1.1
 Date: 29/12/2025
"""

# Import modules
import socket
import os
import logging


# Server configuration constants
QUEUE_SIZE = 10
IP = '0.0.0.0'
PORT = 80
SOCKET_TIMEOUT = 2
HTTP_200 = 'HTTP/1.1 200 OK\r\n'
HTTP_400 = 'HTTP/1.1 400 BAD REQUEST\r\n'
HTTP_403 = 'HTTP/1.1 403 FORBIDDEN\r\n\r\n'
HTTP_404 = 'HTTP/1.1 404 NOT FOUND\r\n\r\n'
HTTP_500 = 'HTTP/1.1 500 INTERNAL SERVER ERROR\r\n\r\n'

# Directory that contains all website files
WEBROOT = 'web_root'

# File returned when requesting "/"
DEFAULT_URL = 'index.html'

# Dictionary of URLs that should be redirected (302)
REDIRECTION_DICTIONARY = {
    '/moved': '/'
}

# Dictionary of file types for Content-Type header
CONTENT_TYPES = {
    'html': 'text/html;charset=utf-8',
    'jpg': 'image/jpeg',
    'css': 'text/css',
    'js': 'text/javascript; charset=UTF-8',
    'txt': 'text/plain',
    'ico': 'image/x-icon',
    'gif': 'image/jpeg',
    'png': 'image/png'
}


def get_file_data(file_name):
    """
    Reads data from a file

    :param file_name: File name
    :return: File data (as bytes)
    """
    # Build the full path to the file
    file_path = os.path.join(WEBROOT, file_name)

    with open(file_path, 'rb') as file:
        return file.read()


def handle_client_request(resource, client_socket):
    """
    Handles the client request – checks what was requested and sends a response
    :param resource: Requested resource (e.g. /index.html)
    :param client_socket: Socket used to communicate with the client
    :return: None
    """

    # If only "/" was requested, return index.html
    if resource == '/':
        uri = DEFAULT_URL
        logging.info(f'The uri is {uri}')
    else:
        # Remove the leading "/" from the resource
        uri = resource.lstrip('/')
        logging.info(f'The uri is {uri}')

    # Special check: if "/forbidden" was requested
    if resource == '/forbidden':
        http_header = HTTP_403
        logging.warning('HTTP/1.1 403 FORBIDDEN')
        client_socket.send(http_header.encode())
        return

    # Special check: if "/error" was requested
    if resource == '/error':
        http_header = HTTP_500
        logging.error('HTTP/1.1 500 INTERNAL SERVER ERROR')
        client_socket.send(http_header.encode())
        return

    # Check if the request should be redirected (302)
    if resource in REDIRECTION_DICTIONARY:
        new_location = REDIRECTION_DICTIONARY[resource]
        http_header = f'HTTP/1.1 302 MOVED TEMPORARILY\r\nLocation: {new_location}\r\n\r\n'
        logging.info('HTTP/1.1 302 MOVED TEMPORARILY')
        client_socket.send(http_header.encode())
        return

    # Build the full path to the requested file
    file_path = os.path.join(WEBROOT, uri)

    # Check if the file exists
    if not os.path.isfile(file_path):
        # File not found – send 404
        http_header = HTTP_404
        logging.warning('HTTP/1.1 404 NOT FOUND')
        client_socket.send(http_header.encode())
        return

    # Extract file extension
    # Example: index.html -> html
    file_extension = uri.split('.')[-1]

    # Get the matching Content-Type
    content_type = CONTENT_TYPES.get(file_extension)

    # Read file content
    try:
        data = get_file_data(uri)
    except Exception as e:
        # Error while reading the file
        http_header = HTTP_500
        logging.error(f'HTTP/1.1 500 INTERNAL SERVER ERROR{e}')
        client_socket.send(http_header.encode())
        return

    # Build the HTTP header
    http_header = HTTP_200
    http_header += f'Content-Type: {content_type}\r\n'
    http_header += f'Content-Length: {len(data)}\r\n'
    http_header += '\r\n'  # Empty line to end headers

    # Send response: header (text) + file data (binary)
    http_response = http_header.encode() + data
    client_socket.send(http_response)


def validate_http_request(request):
    """
    Checks whether the request is a valid HTTP request

    :param request: Request received from the client
    :return: Tuple (True/False if valid, requested resource)
    """

    # Split the request line into parts
    # Example: "GET /index.html HTTP/1.1"
    parts = request.split(' ')

    # Check: must contain at least 3 parts
    if len(parts) < 3:
        logging.error('Invalid HTTP request')
        return False, ''

    # Check: first word must be GET
    if parts[0] != 'GET':
        logging.error('Invalid HTTP request: invalid verb')
        return False, ''

    # Check: HTTP version must start with HTTP/1.1
    if not parts[2].startswith('HTTP/1.1'):
        logging.error('Invalid HTTP request: Version is not 1.1')
        return False, ''

    # The requested resource is the second part
    resource = parts[1]
    logging.info("Valid HTTP request")
    return True, resource


def handle_client(client_socket):
    """
    Handles a client: receives a request, validates it, and responds
    :param client_socket: Socket used to communicate with the client
    :return: None
    """
    print('Client connected')

    try:
        # Receive data from the client character by character
        # until an empty line (\r\n\r\n) is received
        client_request = ''

        while not client_request.endswith('\r\n\r\n'):
            # Read exactly one byte at a time
            char = client_socket.recv(1).decode()
            client_request += char

        # Print the full request
        print(f'Client request:\n{client_request}')

        # Extract only the first line
        first_line = client_request.split('\r\n')[0]
        logging.info(f'First line: {first_line}')

        # Validate the HTTP request
        valid_http, resource = validate_http_request(first_line)

        if valid_http:
            print('Got a valid HTTP request')
            handle_client_request(resource, client_socket)
        else:
            print('Error: Not a valid HTTP request')
            # Send 400 Bad Request
            http_header = HTTP_400
            client_socket.send(http_header.encode())

    except socket.timeout:
        print('Socket timeout - no data received')
    except Exception as e:
        print(f'Error handling client: {e}')
        logging.error(e)

    print('Closing connection')


def main():
    # Main function: opens a socket and waits for clients

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind((IP, PORT))
        server_socket.listen(QUEUE_SIZE)
        print("Listening for connections on port %d" % PORT)

        while True:
            client_socket, client_address = server_socket.accept()
            try:
                print('New connection received')
                client_socket.settimeout(SOCKET_TIMEOUT)
                handle_client(client_socket)
            except socket.error as err:
                print('Received socket exception - ' + str(err))
            finally:
                client_socket.close()
                logging.info('Closing connection')
    except socket.error as err:
        print('Received socket exception - ' + str(err))
    finally:
        server_socket.close()
        logging.info('Closing Server')


if __name__ == "__main__":

    # Logging setup
    logging.basicConfig(
        filename='Server.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Assertions / tests
    valid, resource = validate_http_request('GET / HTTP/1.1')
    assert valid is True, "validate_http_request failed on valid request"
    assert resource == '/', "validate_http_request returned wrong resource"

    # Test: validate_http_request rejects invalid requests
    valid, resource = validate_http_request('POST / HTTP/1.1')  # should log an error
    assert valid is False, "validate_http_request should reject POST"

    # Test: get_file_data reads a file
    if os.path.isfile(os.path.join(WEBROOT, DEFAULT_URL)):
        data = get_file_data(DEFAULT_URL)
        assert data is not None, "get_file_data returned None"
        assert isinstance(data, bytes), "get_file_data should return bytes"

    logging.info('Server started: All assert tests passed successfully')

    main()
