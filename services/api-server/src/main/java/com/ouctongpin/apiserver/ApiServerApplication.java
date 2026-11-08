package com.ouctongpin.apiserver;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@MapperScan("com.ouctongpin.apiserver.**.mapper")
@EnableScheduling
public class ApiServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(ApiServerApplication.class, args);
    }
}
