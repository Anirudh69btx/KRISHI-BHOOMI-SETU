<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('totp') displayInfo=false; section>
    <#if section = "header">
        <div class="flip-brand-header">
            <div class="flip-brand-logo">🌾</div>
            <h1 class="flip-brand-title">Verify OTP Code</h1>
            <div class="flip-brand-tagline">Enter the 6-digit SMS verification code</div>
        </div>
    <#elseif section = "form">
        <form id="kc-otp-login-form" class="form-horizontal" action="${url.loginAction}" method="post">
            <div class="form-group" style="text-align: center;">
                <input id="otp" name="otp" autocomplete="one-time-code" type="text" class="form-control"
                       autofocus maxlength="6" pattern="[0-9]{6}" placeholder="123456"
                       style="font-size: 2rem; letter-spacing: 0.5rem; text-align: center; font-weight: bold; width: 80%; margin: 0 auto 1.5rem auto;" />
            </div>

            <div class="flip-remember-me" style="justify-content: center;">
                <input id="rememberDevice" name="rememberDevice" type="checkbox" checked />
                <label for="rememberDevice">Trust this device for 30 days</label>
            </div>

            <div class="form-group">
                <input class="btn-primary" name="login" id="kc-login" type="submit" value="Verify &amp; Continue →" />
            </div>

            <div style="text-align: center; margin-top: 1.5rem;">
                <a href="${url.loginRestartFlowUrl}" style="color: #059669; font-size: 0.875rem; text-decoration: underline;">
                    ← Back to Phone Number Entry
                </a>
            </div>
        </form>
    </#if>
</@layout.registrationLayout>
