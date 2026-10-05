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

import org.junit.jupiter.api.Test;

class PageInfoTest {

  @Test
  void totalPages_whenExactMultiple() {
    assertThat(new PageInfo(0, 10, 100).getTotalPages()).isEqualTo(10);
  }

  @Test
  void totalPages_withRemainder_roundsUp() {
    assertThat(new PageInfo(0, 10, 95).getTotalPages()).isEqualTo(10);
  }

  @Test
  void totalPages_fewerThanOnePage() {
    assertThat(new PageInfo(0, 10, 3).getTotalPages()).isEqualTo(1);
  }

  @Test
  void totalPages_zeroRecords() {
    assertThat(new PageInfo(0, 10, 0).getTotalPages()).isZero();
  }
}
