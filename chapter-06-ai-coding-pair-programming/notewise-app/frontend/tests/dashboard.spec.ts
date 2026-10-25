import { test, expect } from '@playwright/test';

test.describe('Kiểm thử giao diện NoteWise', () => {
  
  test('Kiểm tra trang Auth và Đăng nhập thành công', async ({ page }) => {
    // 1. Truy cập vào trang Auth/Đăng nhập
    await page.goto('http://localhost:3000/login');

    // 2. Điền thông tin Đăng nhập (thay selector/input phù hợp với giao diện của bạn)
    await page.fill('input[type="email"]', 'duthinhuyen2005@gmail.com');
    await page.fill('input[type="password"]', 'duthinhuyen2005');

    // 3. Nhấn nút Đăng nhập
    await page.click('button[type="submit"]');

    // 4. Kiểm tra xem có chuyển hướng thành công sang trang /dashboard không
    await expect(page).toHaveURL('http://localhost:3000');

    // 5. Kiểm tra tiêu đề "NoteWise" có xuất hiện trên màn hình không
    await expect(page.locator('h1')).toContainText('Welcome back');
  });

});