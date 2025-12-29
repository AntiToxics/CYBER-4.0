"""
 Name: "Server.py"
 Author: Barak Gonen and Nir Dweck and Gilad Elran
 Purpose: Provide a basis for Ex. 4
 Date: 29/12/2025
"""

# ייבוא מודולים
import socket
import os
import logging



# קבועים - הגדרות השרת
QUEUE_SIZE = 10
IP = '0.0.0.0'
PORT = 80
SOCKET_TIMEOUT = 2

# התיקייה שבה נמצאים כל הקבצים של האתר
WEBROOT = 'web_root'

# הקובץ שנחזיר כשמבקשים את /
DEFAULT_URL = 'index.html'

# מילון של URL שצריך להפנות אותם למקום אחר (302)
REDIRECTION_DICTIONARY = {
    '/moved': '/'
}

# מילון של סוגי קבצים - מה לשלוח ב-Content-Type
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
    קורא נתונים מקובץ
    :param file_name: שם הקובץ
    :return: הנתונים מהקובץ (בתור bytes)
    """
    # בונה את הנתיב המלא לקובץ
    file_path = os.path.join(WEBROOT, file_name)

    with open(file_path, 'rb') as file:
        return file.read()


def handle_client_request(resource, client_socket):
    """
    מטפל בבקשה של הלקוח - בודק מה הוא רוצה ושולח תשובה
    :param resource: המשאב שהלקוח ביקש (למשל /index.html)
    :param client_socket: הסוקט לתקשורת עם הלקוח
    :return: None
    """

    # אם ביקשו את / בלבד - נחזיר את index.html
    if resource == '/' or resource == '':
        uri = DEFAULT_URL
        logging.info(f'The uri is {uri}')
    else:
        # מסירים את ה-/ מההתחלה
        uri = resource.lstrip('/')
        logging.info(f'The uri is {uri}')

    # בדיקה מיוחדת: אם ביקשו /forbidden
    if resource == '/forbidden':
        http_header = 'HTTP/1.1 403 FORBIDDEN\r\n\r\n'
        logging.warning('HTTP/1.1 403 FORBIDDEN')
        client_socket.send(http_header.encode())
        return

    # בדיקה מיוחדת: אם ביקשו /error
    if resource == '/error':
        http_header = 'HTTP/1.1 500 INTERNAL SERVER ERROR\r\n\r\n'
        logging.error('HTTP/1.1 500 INTERNAL SERVER ERROR')
        client_socket.send(http_header.encode())
        return

    # בדיקה: אם צריך להפנות למקום אחר (302)
    if resource in REDIRECTION_DICTIONARY:
        new_location = REDIRECTION_DICTIONARY[resource]
        http_header = f'HTTP/1.1 302 MOVED TEMPORARILY\r\nLocation: {new_location}\r\n\r\n'
        logging.info('HTTP/1.1 302 MOVED TEMPORARILY')
        client_socket.send(http_header.encode())
        return

    # בונה את הנתיב המלא לקובץ
    file_path = os.path.join(WEBROOT, uri)

    # בודק אם הקובץ קיים
    if not os.path.isfile(file_path):
        # הקובץ לא נמצא - שולח 404
        http_header = 'HTTP/1.1 404 NOT FOUND\r\n\r\n'
        logging.warning('HTTP/1.1 404 NOT FOUND')
        client_socket.send(http_header.encode())
        return

    # מוצא את סוג הקובץ (הסיומת)
    # למשל: index.html -> html
    file_extension = uri.split('.')[-1]

    # מוצא את ה-Content-Type המתאים
    content_type = CONTENT_TYPES.get(file_extension, 'text/plain')

    # קורא את תוכן הקובץ
    try:
        data = get_file_data(uri)
    except Exception as e:
        # אם יש בעיה בקריאת הקובץ
        http_header = 'HTTP/1.1 500 INTERNAL SERVER ERROR\r\n\r\n'
        logging.error(f'HTTP/1.1 500 INTERNAL SERVER ERROR{e}')
        client_socket.send(http_header.encode())
        return

    # בונה את ה-HTTP Header
    http_header = 'HTTP/1.1 200 OK\r\n'
    http_header += f'Content-Type: {content_type}\r\n'
    http_header += f'Content-Length: {len(data)}\r\n'
    http_header += '\r\n'  # שורה ריקה לסיום ההדרים

    # שולח את התשובה: ההדר (טקסט) + הנתונים (בינארי)
    http_response = http_header.encode() + data
    client_socket.send(http_response)


def validate_http_request(request):
    """
    בודק אם הבקשה היא בקשת HTTP תקינה
    :param request: הבקשה שהתקבלה מהלקוח
    :return: tuple של (True/False האם תקין, המשאב שביקשו)
    """

    # מפרק את הבקשה למילים
    # למשל: "GET /index.html HTTP/1.1" -> ["GET", "/index.html", "HTTP/1.1"]
    parts = request.split(' ')

    # בדיקה: חייבות להיות לפחות 3 מילים
    if len(parts) < 3:
        logging.error('Invalid HTTP request')
        return False, ''


    # בדיקה: המילה הראשונה חייבת להיות GET
    if parts[0] != 'GET':
        logging.error('Invalid HTTP request: invalid verb')
        return False, ''

    # בדיקה: המילה השלישית חייבת להתחיל ב-HTTP/1.1
    if not parts[2].startswith('HTTP/1.1'):
        logging.error('Invalid HTTP request: Version is not 1.1')
        return False, ''

    # המשאב שביקשו הוא המילה השנייה
    resource = parts[1]
    logging.info("Valid HTTP request")
    return True, resource


def handle_client(client_socket):
    """
    מטפל בלקוח: מקבל בקשה, בודק שהיא תקינה, ועונה
    :param client_socket: הסוקט לתקשורת עם הלקוח
    :return: None
    """
    print('Client connected')

    try:
        # מקבל נתונים מהלקוח תו אחר תו עד שמגיעה שורה ריקה (\r\n\r\n)
        client_request = ''

        # קורא תו אחר תו עד שרואים שורה ריקה
        while True:
            # קורא בדיוק תו אחד כל פעם (1 בייט)
            char = client_socket.recv(1).decode()
            client_request += char

            # בודק אם הגענו לסוף ההדרים (שורה ריקה)
            if client_request.endswith('\r\n\r\n'):
                break

        # מדפיס את הבקשה כדי לראות מה התקבל
        print(f'Client request:\n{client_request}')

        # לוקח רק את השורה הראשונה (זה מה שמעניין אותנו)
        first_line = client_request.split('\r\n')[0]
        logging.info(f'First line: {first_line}')

        # בודק אם הבקשה תקינה
        valid_http, resource = validate_http_request(first_line)

        if valid_http:
            print('Got a valid HTTP request')
            handle_client_request(resource, client_socket)
        else:
            print('Error: Not a valid HTTP request')
            # שולח שגיאה 400
            http_header = 'HTTP/1.1 400 BAD REQUEST\r\n\r\n'
            client_socket.send(http_header.encode())

    except socket.timeout:
        print('Socket timeout - no data received')
    except Exception as e:
        print(f'Error handling client: {e}')
        logging.error(e)

    print('Closing connection')


def main():
    # main function: פותחת סוקט ומחכה ללקוחות

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
                print('received socket exception - ' + str(err))
            finally:
                client_socket.close()
                logging.info('Closing connection')
    except socket.error as err:
        print('received socket exception - ' + str(err))
    finally:
        server_socket.close()
        logging.info('Closing Server')


if __name__ == "__main__":

    # Logging setup
    # ------------------------------
    logging.basicConfig(
        filename='Server.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    #------------------------------


    main()


    #asserts
    # -----------------------------------

    valid, resource = validate_http_request('GET / HTTP/1.1')
    assert valid == True, "validate_http_request failed on valid request"
    assert resource == '/', "validate_http_request returned wrong resource"

    # בדיקה: validate_http_request דוחה בקשה לא תקינה
    valid, resource = validate_http_request('POST / HTTP/1.1')
    assert valid == False, "validate_http_request should reject POST"

    # בדיקה: get_file_data קוראת קובץ
    if os.path.isfile(os.path.join(WEBROOT, DEFAULT_URL)):
        data = get_file_data(DEFAULT_URL)
        assert data is not None, "get_file_data returned None"
        assert isinstance(data, bytes), "get_file_data should return bytes"

    logging.info('Server started: All assert tests passed successfully')
    # -----------------------------------
