/* Runtime ABI for the ARM Cortex-M0  
 * idiv.S: signed 32 bit division (only quotient)
 *
 * Copyright (c) 2012-2017 Jörg Mische <bobbl@gmx.de>
 *
 * Permission to use, copy, modify, and/or distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
 * OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */



	.syntax unified
	.text
	.thumb
	.cpu cortex-m0



@ int __divsi3(int num, int denom)
@
@ libgcc wrapper: just an alias for __aeabi_idivmod(), the remainder is ignored
@
	.thumb_func
        .global __divsi3
__divsi3:



@ int __aeabi_idiv(int num:r0, int denom:r1)
@
@ Divide r0 by r1 and return quotient in r0 (all signed).
@ Use __aeabi_uidivmod() but check signs before and change signs afterwards.
@
	.thumb_func
        .global __aeabi_idiv
__aeabi_idiv:

	cmp	r0, #0
	bge	.Lnumerator_pos
	rsbs	r0, r0, #0		@ num = -num
	cmp	r1, #0
	bge	.Lneg_result
	rsbs	r1, r1, #0		@ den = -den

.Luidivmod:
	b	__aeabi_uidivmod

.Lnumerator_pos:
	cmp	r1, #0
	bge	.Luidivmod
	rsbs	r1, r1, #0		@ den = -den

.Lneg_result:
	push	{lr}
	bl	__aeabi_uidivmod
	rsbs	r0, r0, #0		@ quot = -quot
	pop	{pc}
