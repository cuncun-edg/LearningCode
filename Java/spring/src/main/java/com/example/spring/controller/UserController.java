package com.example.spring.controller;

import com.example.spring.pojo.Result;
import com.example.spring.pojo.User;
import com.example.spring.service.UserService;
import com.example.spring.utils.JwtUtil;
import com.example.spring.utils.Md5Util;
import jakarta.validation.constraints.Pattern;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/user")
@Validated
public class UserController {
    @Autowired
    private UserService userService;

    @PostMapping("/register")
    public Result register(@Pattern(regexp = "^\\S{5,16}$") String username, @Pattern(regexp = "^\\S{5,16}$") String password){
        //查询用户
        User user = userService.findByUserName(username);
        if (user == null){
            //用户不存在,注册
            userService.register(username, password);
            return Result.success();
        }else{
            //用户已存在
            return Result.error("用户已经存在");
        }
    }
    @PostMapping("/login")
    public Result<String> login(@Pattern(regexp = "^\\S{5,16}$") String username, @Pattern(regexp = "^\\S{5,16}$") String password){
        User loginUser = userService.findByUserName(username);

        if(loginUser == null){
            return Result.error("没有这个用户");
        }

        if(Md5Util.getMD5String(password).equals(loginUser.getPassword())){
            //登陆成功
//            return Result.success("jwt token令牌");
            Map<String,Object> claims = new HashMap<>();
            claims.put("id", loginUser.getId());
            claims.put("username", loginUser.getUsername());
            String token = JwtUtil.genToken(claims);
            return Result.success(token);
            //把token存储到redis中
//            ValueOperations<String, String> operations = stringRedisTemplate.opsForValue();
//            operations.set(token, token, 1, TimeUnit.HOURS);
//            return Result.success(token);
        }

        return Result.error("密码错误");
    }

    @GetMapping("/userInfo")
    public Result<User> userInfo(@RequestHeader(name = "Authorization") String token){

        //根据用户名查找用户
        Map<String, Object> claims = JwtUtil.parseToken(token);
        String username = (String) claims.get("username");

//        Map<String, Object> map = ThreadLocalUtil.get();
//        String username = (String) map.get("username");
        User user = userService.findByUserName(username);
        return Result.success(user);
    }
}

