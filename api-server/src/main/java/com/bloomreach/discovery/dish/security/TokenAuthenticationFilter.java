package com.bloomreach.discovery.dish.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.ArrayList;

public class TokenAuthenticationFilter extends OncePerRequestFilter {

    private static final String TOKEN_HEADER = "x-dish-access-token";
    private final String accessToken;

    public TokenAuthenticationFilter(String accessToken) {
        this.accessToken = accessToken;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                  HttpServletResponse response,
                                  FilterChain filterChain) throws ServletException, IOException {
        
        String token = request.getHeader(TOKEN_HEADER);

        if (token != null && token.equals(accessToken)) {
            SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken("dish-service", null, new ArrayList<>())
            );
        }

        filterChain.doFilter(request, response);
    }
}