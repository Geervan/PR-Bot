"""
Test script for multi-language code parser.
"""

import os

# Set mock env vars before importing app modules
os.environ["GEMINI_API_KEYS"] = "fake_key"
os.environ["APP_ID"] = "123"
os.environ["PRIVATE_KEY_PATH"] = "fake_path"
os.environ["WEBHOOK_SECRET"] = "fake_secret"

from app.core.code_parser import code_parser, CodeSymbols


def test_python():
    """Test Python parsing."""
    print("\n" + "=" * 60)
    print("TEST: Python")
    print("=" * 60)
    
    code = """
import os
from typing import List, Dict

class UserService:
    def get_user(self, id: int) -> Dict:
        return {"id": id}

def main():
    service = UserService()
    user = service.get_user(1)
    print(user)
"""
    
    symbols = code_parser.parse(code, "app/service.py")
    
    print(f"📦 Language: {symbols.language}")
    print(f"📦 Imports: {symbols.imports}")
    print(f"📦 From Imports: {symbols.from_imports}")
    print(f"🏗️ Classes: {symbols.classes}")
    print(f"🔧 Functions: {symbols.functions}")
    
    assert symbols.language == "python"
    assert "os" in symbols.imports
    assert len(symbols.classes) >= 1
    assert "main" in symbols.functions
    
    print("✅ Python test PASSED!")


def test_javascript():
    """Test JavaScript parsing."""
    print("\n" + "=" * 60)
    print("TEST: JavaScript")
    print("=" * 60)
    
    code = """
import React from 'react';
import { useState } from 'react';

class Component extends React.Component {
    render() {
        return <div>Hello</div>;
    }
}

function App() {
    const [count, setCount] = useState(0);
    return <div>{count}</div>;
}

const helper = () => console.log('hi');
"""
    
    symbols = code_parser.parse(code, "app/App.jsx")
    
    print(f"📦 Language: {symbols.language}")
    print(f"📦 Imports: {symbols.imports}")
    print(f"🏗️ Classes: {symbols.classes}")
    print(f"🔧 Functions: {symbols.functions}")
    
    assert symbols.language == "javascript"
    assert "react" in symbols.imports
    assert "Component" in symbols.classes
    assert "App" in symbols.functions
    
    print("✅ JavaScript test PASSED!")


def test_typescript():
    """Test TypeScript parsing."""
    print("\n" + "=" * 60)
    print("TEST: TypeScript")
    print("=" * 60)
    
    code = """
import axios from 'axios';

interface User {
    id: number;
    name: string;
}

class UserAPI {
    async getUser(id: number): Promise<User> {
        const response = await axios.get(`/users/${id}`);
        return response.data;
    }
}

function createUser(name: string): User {
    return { id: 1, name };
}
"""
    
    symbols = code_parser.parse(code, "api/user.ts")
    
    print(f"📦 Language: {symbols.language}")
    print(f"📦 Imports: {symbols.imports}")
    print(f"🏗️ Classes: {symbols.classes}")
    print(f"🔧 Functions: {symbols.functions}")
    
    assert symbols.language == "typescript"
    assert "axios" in symbols.imports
    assert "UserAPI" in symbols.classes
    assert "createUser" in symbols.functions
    
    print("✅ TypeScript test PASSED!")


def test_java():
    """Test Java parsing."""
    print("\n" + "=" * 60)
    print("TEST: Java")
    print("=" * 60)
    
    code = """
package com.example;

import java.util.List;
import java.util.ArrayList;

public class UserService {
    private List<User> users = new ArrayList<>();
    
    public User findById(Long id) {
        return users.stream()
            .filter(u -> u.getId().equals(id))
            .findFirst()
            .orElse(null);
    }
    
    public void addUser(User user) {
        users.add(user);
    }
}
"""
    
    symbols = code_parser.parse(code, "UserService.java")
    
    print(f"📦 Language: {symbols.language}")
    print(f"📦 Imports: {symbols.imports}")
    print(f"🏗️ Classes: {symbols.classes}")
    print(f"🔧 Functions: {symbols.functions}")
    
    assert symbols.language == "java"
    assert any("List" in imp for imp in symbols.imports)
    assert "UserService" in symbols.classes
    assert "findById" in symbols.functions
    
    print("✅ Java test PASSED!")


def test_go():
    """Test Go parsing."""
    print("\n" + "=" * 60)
    print("TEST: Go")
    print("=" * 60)
    
    code = """
package main

import (
    "fmt"
    "net/http"
)

type User struct {
    ID   int
    Name string
}

func (u *User) String() string {
    return fmt.Sprintf("User{ID: %d, Name: %s}", u.ID, u.Name)
}

func GetUser(id int) *User {
    return &User{ID: id, Name: "John"}
}

func main() {
    user := GetUser(1)
    fmt.Println(user)
}
"""
    
    symbols = code_parser.parse(code, "main.go")
    
    print(f"📦 Language: {symbols.language}")
    print(f"📦 Imports: {symbols.imports}")
    print(f"🏗️ Types: {symbols.classes}")
    print(f"🔧 Functions: {symbols.functions}")
    
    assert symbols.language == "go"
    assert "fmt" in symbols.imports
    assert "User" in symbols.classes
    assert "GetUser" in symbols.functions or "main" in symbols.functions
    
    print("✅ Go test PASSED!")


def test_rust():
    """Test Rust parsing."""
    print("\n" + "=" * 60)
    print("TEST: Rust")
    print("=" * 60)
    
    code = """
use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct User {
    id: u32,
    name: String,
}

impl User {
    fn new(id: u32, name: String) -> Self {
        User { id, name }
    }
}

fn get_user(id: u32) -> Option<User> {
    Some(User::new(id, "John".to_string()))
}

fn main() {
    let user = get_user(1);
    println!("{:?}", user);
}
"""
    
    symbols = code_parser.parse(code, "main.rs")
    
    print(f"📦 Language: {symbols.language}")
    print(f"📦 Imports: {symbols.imports}")
    print(f"🏗️ Structs: {symbols.classes}")
    print(f"🔧 Functions: {symbols.functions}")
    
    assert symbols.language == "rust"
    assert any("HashMap" in imp or "std" in imp for imp in symbols.imports)
    assert "User" in symbols.classes
    assert "get_user" in symbols.functions or "main" in symbols.functions
    
    print("✅ Rust test PASSED!")


def test_cpp():
    """Test C++ parsing."""
    print("\n" + "=" * 60)
    print("TEST: C++")
    print("=" * 60)
    
    code = """
#include <iostream>
#include <vector>
#include "user.h"

class UserManager {
public:
    void addUser(const User& user) {
        users.push_back(user);
    }
    
    User* findById(int id) {
        for (auto& user : users) {
            if (user.id == id) return &user;
        }
        return nullptr;
    }
    
private:
    std::vector<User> users;
};

int main() {
    UserManager manager;
    return 0;
}
"""
    
    symbols = code_parser.parse(code, "main.cpp")
    
    print(f"📦 Language: {symbols.language}")
    print(f"📦 Includes: {symbols.imports}")
    print(f"🏗️ Classes: {symbols.classes}")
    print(f"🔧 Functions: {symbols.functions}")
    
    assert symbols.language == "cpp"
    assert "iostream" in symbols.imports
    assert "UserManager" in symbols.classes
    assert "main" in symbols.functions
    
    print("✅ C++ test PASSED!")


def test_summary():
    """Test summary generation."""
    print("\n" + "=" * 60)
    print("TEST: Summary Generation")
    print("=" * 60)
    
    code = """
import os
from typing import List

class MyClass:
    pass

def my_function():
    pass
"""
    
    summary = code_parser.get_summary(code, "test.py")
    
    print(f"📝 Summary:\n{summary}")
    
    assert "python" in summary.lower() or "Python" in summary
    assert "MyClass" in summary
    assert "my_function" in summary
    
    print("✅ Summary test PASSED!")


if __name__ == "__main__":
    try:
        test_python()
        test_javascript()
        test_typescript()
        test_java()
        test_go()
        test_rust()
        test_cpp()
        test_summary()
        
        print("\n" + "=" * 60)
        print("🎉 ALL MULTI-LANGUAGE TESTS PASSED!")
        print("=" * 60)
        print("\nSupported languages:")
        print("  ✅ Python")
        print("  ✅ JavaScript/JSX")
        print("  ✅ TypeScript/TSX")
        print("  ✅ Java")
        print("  ✅ Go")
        print("  ✅ Rust")
        print("  ✅ C/C++")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
