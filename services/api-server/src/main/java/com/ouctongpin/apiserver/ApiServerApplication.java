package com.ouctongpin.apiserver;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.ouctongpin.apiserver.**.mapper")
public class ApiServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(ApiServerApplication.class, args);
    }
}
