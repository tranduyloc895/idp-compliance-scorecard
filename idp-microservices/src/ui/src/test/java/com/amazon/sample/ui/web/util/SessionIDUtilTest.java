/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this
 * software and associated documentation files (the "Software"), to deal in the Software
 * without restriction, including without limitation the rights to use, copy, modify,
 * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

package com.amazon.sample.ui.web.util;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.web.server.ServerWebExchange;

class SessionIDUtilTest {

  @Test
  void getSessionId_returnsHeaderValue() {
    ServerHttpRequest request = MockServerHttpRequest
      .get("/")
      .header(SessionIDUtil.HEADER_NAME, "abc-123")
      .build();
    assertThat(SessionIDUtil.getSessionId(request)).isEqualTo("abc-123");
  }

  @Test
  void getSessionId_returnsNullWhenHeaderAbsent() {
    ServerHttpRequest request = MockServerHttpRequest.get("/").build();
    assertThat(SessionIDUtil.getSessionId(request)).isNull();
  }

  @Test
  void addSessionCookie_setsCookieAndReturnsUuid() {
    ServerWebExchange exchange = MockServerWebExchange.from(
      MockServerHttpRequest.get("/").build()
    );

    String sessionId = SessionIDUtil.addSessionCookie(exchange);

    // trả về một UUID hợp lệ
    assertThat(UUID.fromString(sessionId)).isNotNull();
    // cookie SESSIONID được set đúng giá trị vừa sinh
    assertThat(
      exchange.getResponse().getCookies().getFirst(SessionIDUtil.COOKIE_NAME)
    )
      .isNotNull()
      .extracting(cookie -> cookie.getValue())
      .isEqualTo(sessionId);
  }

  @Test
  void constructor_isNotInstantiable() {
    // class util: constructor protected ném UnsupportedOperationException
    assertThatThrownBy(() -> new SessionIDUtil())
      .isInstanceOf(UnsupportedOperationException.class);
  }
}
