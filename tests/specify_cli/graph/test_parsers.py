"""Tests for language parsers."""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.graph.parsers import get_parser_for_path
from specify_cli.graph.parsers.data_ml_parser import DataMLParser
from specify_cli.graph.parsers.go_parser import GoParser
from specify_cli.graph.parsers.jvm_parser import JVMParser
from specify_cli.graph.parsers.native_parser import NativeParser
from specify_cli.graph.parsers.python_parser import PythonParser
from specify_cli.graph.parsers.rust_parser import RustParser
from specify_cli.graph.parsers.web_parser import WebParser


def test_parser_registry():
    assert isinstance(get_parser_for_path(Path("app.py")), PythonParser)
    assert isinstance(get_parser_for_path(Path("index.ts")), WebParser)
    assert isinstance(get_parser_for_path(Path("Component.vue")), WebParser)
    assert isinstance(get_parser_for_path(Path("main.go")), GoParser)
    assert isinstance(get_parser_for_path(Path("lib.rs")), RustParser)
    assert isinstance(get_parser_for_path(Path("App.java")), JVMParser)
    assert isinstance(get_parser_for_path(Path("Server.cs")), NativeParser)
    assert isinstance(get_parser_for_path(Path("main.cpp")), NativeParser)
    assert isinstance(get_parser_for_path(Path("notebook.ipynb")), DataMLParser)
    assert isinstance(get_parser_for_path(Path("schema.sql")), DataMLParser)
    assert isinstance(get_parser_for_path(Path("service.proto")), DataMLParser)
    assert get_parser_for_path(Path("image.png")) is None
    assert get_parser_for_path(Path("README.md")) is None


def test_python_parser():
    code = '''
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    id: int
    name: str

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Retrieve user by ID."""
    return {"id": user_id}

@app.post("/users")
def create_user(user: User):
    return user
'''
    parser = PythonParser()
    p = Path("backend/api.py")
    imports, symbols, routes, models = parser.parse(p, str(p), code)

    assert any("fastapi" in imp for imp in imports)
    assert any("pydantic" in imp for imp in imports)

    # Check models
    model_names = [m.name for m in models]
    assert "User" in model_names
    user_model = next(m for m in models if m.name == "User")
    assert user_model.kind == "pydantic"
    assert "id" in user_model.fields
    assert "name" in user_model.fields

    # Check routes
    route_paths = [r.path for r in routes]
    assert "/users/{user_id}" in route_paths
    assert "/users" in route_paths
    get_route = next(r for r in routes if r.path == "/users/{user_id}")
    assert get_route.method == "GET"
    assert "get_user" in get_route.handler_symbol

    # Check symbols
    symbol_names = [s.name for s in symbols]
    assert "User" in symbol_names
    assert "get_user" in symbol_names
    assert "create_user" in symbol_names


def test_web_parser_typescript_and_nextjs():
    code = '''
import { z } from 'zod';
import express from 'express';

export const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
});

export interface AuthContext {
  token: string;
}

const app = express();

app.get('/api/health', (req, res) => {
  res.send('ok');
});

export async function GET(request: Request) {
  return Response.json({ status: "ok" });
}
'''
    parser = WebParser()
    p = Path("src/app/api/v1/route.ts")
    imports, symbols, routes, models = parser.parse(p, str(p), code)

    assert any("zod" in imp for imp in imports)
    assert any("express" in imp for imp in imports)

    # Models: Zod schema
    model_names = [m.name for m in models]
    assert "UserSchema" in model_names

    # Symbols: Interface & functions
    symbol_names = [s.name for s in symbols]
    assert "AuthContext" in symbol_names
    assert "GET" in symbol_names

    # Routes: Next.js App Router inferred from filename + express route
    route_paths = [r.path for r in routes]
    assert "/api/health" in route_paths
    assert any("api/v1" in r.path for r in routes)


def test_go_parser():
    code = '''
package main

import (
    "net/http"
    "github.com/gin-gonic/gin"
)

type Customer struct {
    ID   string
    Name string
}

type Service interface {
    GetCustomer(id string) (*Customer, error)
}

func (s *Server) HandleGet(c *gin.Context) {
    c.JSON(200, gin.H{"status": "ok"})
}

func main() {
    r := gin.Default()
    r.GET("/api/customers", s.HandleGet)
}
'''
    parser = GoParser()
    p = Path("server.go")
    imports, symbols, routes, models = parser.parse(p, str(p), code)

    assert any("net/http" in imp for imp in imports)
    assert any("github.com/gin-gonic/gin" in imp for imp in imports)

    # Structs & interfaces
    model_names = [m.name for m in models]
    assert "Customer" in model_names

    symbol_names = [s.name for s in symbols]
    assert "Customer" in symbol_names
    assert "Service" in symbol_names
    assert "Server.HandleGet" in symbol_names
    assert "main" in symbol_names

    # Routes
    route_paths = [r.path for r in routes]
    assert "/api/customers" in route_paths


def test_rust_parser():
    code = '''
use actix_web::{get, post, web, HttpResponse, Responder};

pub struct Profile {
    pub username: String,
}

pub enum Role {
    Admin,
    User,
}

pub trait AuthProvider {
    fn verify(&self, token: &str) -> bool;
}

#[get("/profile")]
pub async fn get_profile() -> impl Responder {
    HttpResponse::Ok().body("profile")
}
'''
    parser = RustParser()
    p = Path("src/handlers.rs")
    imports, symbols, routes, models = parser.parse(p, str(p), code)

    assert any("actix_web" in imp for imp in imports)

    model_names = [m.name for m in models]
    assert "Profile" in model_names

    symbol_names = [s.name for s in symbols]
    assert "Profile" in symbol_names
    assert "Role" in symbol_names
    assert "AuthProvider" in symbol_names
    assert "get_profile" in symbol_names

    route_paths = [r.path for r in routes]
    assert "/profile" in route_paths


def test_jvm_parser():
    code = '''
package com.example.demo;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {
    
    @GetMapping("/api/orders")
    public List<Order> getOrders() {
        return List.of();
    }
}
'''
    parser = JVMParser()
    p = Path("OrderController.java")
    imports, symbols, routes, models = parser.parse(p, str(p), code)

    assert any("springframework" in imp for imp in imports)

    symbol_names = [s.name for s in symbols]
    assert "OrderController" in symbol_names

    route_paths = [r.path for r in routes]
    assert "/api/orders" in route_paths


def test_native_parser():
    code = '''
#include <iostream>
#include "service.h"

class EngineController {
public:
    void StartEngine();
};

[ApiController]
[Route("api/[controller]")]
public class WeatherForecastController : ControllerBase {
    [HttpGet("forecast")]
    public IEnumerable<WeatherForecast> Get() {
        return null;
    }
}
'''
    parser = NativeParser()
    p = Path("Controller.cs")
    imports, symbols, routes, models = parser.parse(p, str(p), code)

    assert "service.h" in imports
    symbol_names = [s.name for s in symbols]
    assert "EngineController" in symbol_names
    assert "WeatherForecastController" in symbol_names

    route_paths = [r.path for r in routes]
    assert any("forecast" in p for p in route_paths)


def test_data_ml_parser():
    # 1. SQL
    sql_code = '''
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''
    parser = DataMLParser()
    p_sql = Path("schema.sql")
    imports, symbols, routes, models = parser.parse(p_sql, str(p_sql), sql_code)
    model_names = [m.name for m in models]
    assert "customers" in model_names

    # 2. Proto
    proto_code = '''
syntax = "proto3";
package ecommerce;

service PaymentService {
    rpc ProcessPayment (PaymentRequest) returns (PaymentResponse);
}

message PaymentRequest {
    string user_id = 1;
    double amount = 2;
}
'''
    p_proto = Path("payment.proto")
    imports, symbols, routes, models = parser.parse(p_proto, str(p_proto), proto_code)
    assert any(s.name == "PaymentService" for s in symbols)
    assert any(s.name == "PaymentRequest" for s in symbols)
    assert any(r.path == "ProcessPayment" for r in routes)

    # 3. Jupyter Notebook
    notebook_dict = {
        "cells": [
            {
                "cell_type": "code",
                "source": [
                    "import pandas as pd\n",
                    "import torch\n",
                    "\n",
                    "def train_model():\n",
                    "    pass\n"
                ]
            }
        ]
    }
    p_nb = Path("train.ipynb")
    imports, symbols, routes, models = parser.parse(p_nb, str(p_nb), json.dumps(notebook_dict))
    assert "pandas" in imports
    assert "torch" in imports
    assert any("train" in s.name for s in symbols)
