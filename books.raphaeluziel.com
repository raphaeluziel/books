server {
    listen 80;
    listen [::]:80;
    
    server_name books.raphaeluziel.com;

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/raphaeluziel/books/books.sock;
    }
}
