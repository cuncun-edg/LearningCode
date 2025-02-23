package com.example.spring.service.impl;

import com.example.spring.mapper.UserMapper;
import com.example.spring.pojo.User;
import com.example.spring.service.UserService;
import com.example.spring.utils.Md5Util;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class UserServiceImpl implements UserService {
    @Autowired
    private UserMapper userMapper;
    @Override
    public User findByUserName(String username) {
        User user = userMapper.findByUserName(username);
        return user;
    }

    @Override
    public void register(String username, String password) {
        //加密
        String md5string = Md5Util.getMD5String(password);
        //添加用户
        userMapper.add(username, md5string);

    }
}
