package com.bloomreach.discovery.dish;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class DishApplication {

	public static void main(String[] args) {
		SpringApplication.run(DishApplication.class, args);
	}

}
