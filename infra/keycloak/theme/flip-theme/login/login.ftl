<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username','password') displayInfo=realm.password && realm.registrationAllowed && !registrationDisabled??; section>
    <#if section = "header">
        <div class="flip-brand-header">
            <div class="flip-brand-logo">🌾</div>
            <h1 class="flip-brand-title">KRISHI BHOOMI SETU</h1>
            <div class="flip-brand-tagline">FLIP v3.0 — Kisan Voice Copilot &amp; Intelligence</div>
        </div>
    <#elseif section = "form">
        <div id="kc-form">
            <div id="kc-form-wrapper">
                <#if realm.password>
                    <form id="kc-form-login" onsubmit="login.disabled = true; return true;" action="${url.loginAction}" method="post">
                        <div class="form-group">
                            <label for="username" class="control-label">Mobile Number / Username / Email</label>
                            <input tabindex="1" id="username" class="form-control" name="username" value="${(login.username!'')}" type="text" autofocus autocomplete="username" placeholder="+91 98765 43210" required />
                        </div>

                        <div class="form-group">
                            <label for="password" class="control-label">Password (Optional for Farmer Phone OTP)</label>
                            <input tabindex="2" id="password" class="form-control" name="password" type="password" autocomplete="current-password" placeholder="••••••••" />
                        </div>

                        <div class="flip-remember-me">
                            <input tabindex="3" id="rememberMe" name="rememberMe" type="checkbox" checked />
                            <label for="rememberMe">Remember me on this device (30-day trusted session)</label>
                        </div>

                        <div id="kc-form-buttons" class="form-group">
                            <input tabindex="4" class="btn-primary" name="login" id="kc-login" type="submit" value="Sign In / Get OTP →" />
                        </div>
                    </form>
                </#if>

                <div style="margin-top: 1.5rem; text-align: center; border-top: 1px solid #e5e7eb; padding-top: 1.25rem;">
                    <a href="${url.loginAction}?kc_action=webauthn-register" style="color: #059669; font-weight: 600; text-decoration: none; font-size: 0.875rem;">
                        🔑 Sign In with Passkey / Security Key (WebAuthn)
                    </a>
                </div>
            </div>
        </div>
    </#if>
</@layout.registrationLayout>
