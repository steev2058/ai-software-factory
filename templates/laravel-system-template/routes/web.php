<?php
use Illuminate\Support\Facades\Route;
Route::get('/', fn() => view('welcome'));
// Auth routes should be installed via Breeze/Jetstream
