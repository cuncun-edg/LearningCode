package com.example.spring.service;

import com.example.spring.pojo.User;

public interface UserService {
    User findByUserName(String username);

    void register(String username, String password);
}
