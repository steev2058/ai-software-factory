# Laravel System Template

## Install
```bash
composer install
cp .env.example .env
php artisan key:generate
php artisan migrate
```

## Run (dev)
```bash
php artisan serve
```

## Build / optimize
```bash
php artisan config:cache
php artisan route:cache
php artisan view:cache
```
