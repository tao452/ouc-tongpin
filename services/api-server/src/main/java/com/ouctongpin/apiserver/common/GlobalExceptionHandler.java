package com.ouctongpin.apiserver.common;

import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    // Preserve moderation's 422/503 instead of converting them into an HTTP 200 error envelope.
    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Result<?>> handleResponseStatusException(ResponseStatusException e) {
        int status = e.getStatusCode().value();
        String message = switch (status) {
            case 422 -> "内容未通过安全检查";
            case 503 -> "内容安全服务暂不可用，请稍后重试";
            default -> "请求未通过检查";
        };
        return ResponseEntity.status(e.getStatusCode()).body(Result.fail(status, message));
    }

    // 拦截 @Valid 校验失败抛出的异常
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Result<?>> handleValidException(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldError().getDefaultMessage();
        return ResponseEntity.badRequest().body(Result.fail(1001, msg));
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Result<?>> handleUnreadableBody(HttpMessageNotReadableException e) {
        return ResponseEntity.badRequest().body(Result.fail(400, "请求格式不合法"));
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<Result<?>> handleMissingResource(NoResourceFoundException e) {
        return ResponseEntity.status(404).body(Result.fail(404, "接口不存在"));
    }

    // 拦截系统内部其他异常
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Result<?>> handleException(Exception e) {
        return ResponseEntity.internalServerError().body(Result.fail(500, "服务器内部错误"));
    }
}
