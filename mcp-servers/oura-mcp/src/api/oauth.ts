import axios, { AxiosError } from "axios";
import * as fs from "fs";
import * as path from "path";

// =============================================================================
// CONSTANTS
// =============================================================================

const OURA_OAUTH_BASE_URL = "https://cloud.ouraring.com/oauth";
const OURA_API_BASE_URL = "https://api.ouraring.com/oauth";
const TOKEN_CACHE_DIR = ".cache";
const TOKEN_CACHE_FILE = "oura-tokens.json";

// =============================================================================
// TYPES
// =============================================================================

/**
 * OAuth token response from Oura API
 */
export interface OuraTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
  created_at?: number;
}

/**
 * Stored token data with expiration tracking
 */
export interface StoredTokenData {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_at: number; // Unix timestamp in milliseconds
  created_at: number;
}

/**
 * OAuth configuration
 */
export interface OAuthConfig {
  clientId: string;
  clientSecret: string;
  redirectUri?: string;
}

/**
 * OAuth error details
 */
export interface OAuthError {
  error: string;
  error_description?: string;
}

// =============================================================================
// OAUTH CLIENT
// =============================================================================

/**
 * OAuth client for Oura API authentication
 * Handles token management, refresh, and storage
 */
export class OuraOAuthClient {
  private config: OAuthConfig;
  private tokenCachePath: string;
  private cachedTokens: StoredTokenData | null = null;

  constructor(config?: OAuthConfig) {
    // Load from environment if not provided
    this.config = config || {
      clientId: process.env.OURA_CLIENT_ID || "",
      clientSecret: process.env.OURA_CLIENT_SECRET || "",
      redirectUri: process.env.OURA_REDIRECT_URI,
    };

    // Allow personal access token mode (skip OAuth if PAT is set)
    const personalToken = process.env.OURA_PERSONAL_ACCESS_TOKEN || process.env.OURA_ACCESS_TOKEN;
    if (personalToken) {
      // Personal access token mode - no OAuth needed
      this.tokenCachePath = "";
      return;
    }

    // Validate OAuth configuration (only if not using personal access token)
    if (!this.config.clientId || !this.config.clientSecret) {
      throw new Error(
        "OAuth configuration missing: Set OURA_PERSONAL_ACCESS_TOKEN for simple auth, or OURA_CLIENT_ID and OURA_CLIENT_SECRET for OAuth"
      );
    }

    // Set up token cache path
    const cacheDir = process.env.CACHE_DB_PATH
      ? path.dirname(process.env.CACHE_DB_PATH)
      : TOKEN_CACHE_DIR;
    this.tokenCachePath = path.join(cacheDir, TOKEN_CACHE_FILE);

    // Ensure cache directory exists
    this.ensureCacheDirectory();

    // Load cached tokens on initialization
    this.loadCachedTokens();
  }

  // ===========================================================================
  // TOKEN CACHE MANAGEMENT
  // ===========================================================================

  /**
   * Ensures the cache directory exists
   */
  private ensureCacheDirectory(): void {
    const cacheDir = path.dirname(this.tokenCachePath);
    if (!fs.existsSync(cacheDir)) {
      fs.mkdirSync(cacheDir, { recursive: true });
    }
  }

  /**
   * Loads tokens from cache file
   */
  private loadCachedTokens(): void {
    try {
      if (fs.existsSync(this.tokenCachePath)) {
        const data = fs.readFileSync(this.tokenCachePath, "utf-8");
        this.cachedTokens = JSON.parse(data);
      }
    } catch (error) {
      console.error("[OAuth] Failed to load cached tokens:", error);
      this.cachedTokens = null;
    }
  }

  /**
   * Saves tokens to cache file
   */
  private saveTokensToCache(tokens: StoredTokenData): void {
    try {
      fs.writeFileSync(
        this.tokenCachePath,
        JSON.stringify(tokens, null, 2),
        "utf-8"
      );
      this.cachedTokens = tokens;
    } catch (error) {
      console.error("[OAuth] Failed to save tokens to cache:", error);
      throw new Error("Failed to persist OAuth tokens");
    }
  }

  /**
   * Clears cached tokens
   */
  private clearTokenCache(): void {
    try {
      if (fs.existsSync(this.tokenCachePath)) {
        fs.unlinkSync(this.tokenCachePath);
      }
      this.cachedTokens = null;
    } catch (error) {
      console.error("[OAuth] Failed to clear token cache:", error);
    }
  }

  // ===========================================================================
  // TOKEN VALIDATION & REFRESH
  // ===========================================================================

  /**
   * Checks if a token is expired or will expire soon (within 5 minutes)
   */
  private isTokenExpired(tokens: StoredTokenData): boolean {
    const now = Date.now();
    const bufferTime = 5 * 60 * 1000; // 5 minutes buffer
    return now >= tokens.expires_at - bufferTime;
  }

  /**
   * Converts OAuth token response to stored token data
   */
  private processTokenResponse(response: OuraTokenResponse): StoredTokenData {
    const now = Date.now();
    return {
      access_token: response.access_token,
      refresh_token: response.refresh_token,
      token_type: response.token_type,
      expires_at: now + response.expires_in * 1000,
      created_at: now,
    };
  }

  // ===========================================================================
  // OAUTH FLOWS
  // ===========================================================================

  /**
   * Gets the authorization URL for the OAuth flow
   * Users should visit this URL to authorize the application
   */
  public getAuthorizationUrl(scope?: string, state?: string): string {
    const params = new URLSearchParams({
      client_id: this.config.clientId,
      response_type: "code",
      redirect_uri: this.config.redirectUri || "http://localhost:3000/callback",
      scope: scope || "daily",
      ...(state && { state }),
    });

    return `${OURA_OAUTH_BASE_URL}/authorize?${params.toString()}`;
  }

  /**
   * Exchanges an authorization code for access and refresh tokens
   * This is the second step in the OAuth authorization code flow
   */
  public async exchangeAuthorizationCode(
    code: string
  ): Promise<StoredTokenData> {
    try {
      const response = await axios.post<OuraTokenResponse>(
        `${OURA_API_BASE_URL}/token`,
        new URLSearchParams({
          grant_type: "authorization_code",
          code,
          redirect_uri:
            this.config.redirectUri || "http://localhost:3000/callback",
          client_id: this.config.clientId,
          client_secret: this.config.clientSecret,
        }),
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );

      const tokens = this.processTokenResponse(response.data);
      this.saveTokensToCache(tokens);
      return tokens;
    } catch (error) {
      throw this.handleOAuthError(error, "Failed to exchange authorization code");
    }
  }

  /**
   * Refreshes the access token using a refresh token
   */
  public async refreshAccessToken(
    refreshToken?: string
  ): Promise<StoredTokenData> {
    const tokenToUse =
      refreshToken ||
      this.cachedTokens?.refresh_token ||
      process.env.OURA_REFRESH_TOKEN;

    if (!tokenToUse) {
      throw new Error(
        "No refresh token available. Please re-authenticate using the authorization flow."
      );
    }

    try {
      const response = await axios.post<OuraTokenResponse>(
        `${OURA_API_BASE_URL}/token`,
        new URLSearchParams({
          grant_type: "refresh_token",
          refresh_token: tokenToUse,
          client_id: this.config.clientId,
          client_secret: this.config.clientSecret,
        }),
        {
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        }
      );

      const tokens = this.processTokenResponse(response.data);
      this.saveTokensToCache(tokens);
      return tokens;
    } catch (error) {
      // If refresh fails, clear the cache to force re-authentication
      this.clearTokenCache();
      throw this.handleOAuthError(error, "Failed to refresh access token");
    }
  }

  /**
   * Revokes an access token
   */
  public async revokeToken(accessToken?: string): Promise<void> {
    const tokenToRevoke =
      accessToken ||
      this.cachedTokens?.access_token ||
      process.env.OURA_ACCESS_TOKEN;

    if (!tokenToRevoke) {
      throw new Error("No access token available to revoke");
    }

    try {
      await axios.post(
        `${OURA_API_BASE_URL}/revoke`,
        null,
        {
          params: {
            access_token: tokenToRevoke,
          },
        }
      );

      // Clear cached tokens after successful revocation
      this.clearTokenCache();
    } catch (error) {
      throw this.handleOAuthError(error, "Failed to revoke access token");
    }
  }

  // ===========================================================================
  // TOKEN RETRIEVAL
  // ===========================================================================

  /**
   * Gets a valid access token, refreshing if necessary
   * This is the main method to use when you need an access token for API calls
   */
  public async getValidAccessToken(): Promise<string> {
    // First, try personal access token (simplest auth method)
    const personalToken = process.env.OURA_PERSONAL_ACCESS_TOKEN;
    if (personalToken) {
      return personalToken;
    }

    // Then try legacy access token env var (for testing/development)
    const envToken = process.env.OURA_ACCESS_TOKEN;
    if (envToken && !this.cachedTokens) {
      return envToken;
    }

    // Check if we have cached tokens
    if (!this.cachedTokens) {
      throw new Error(
        "No access token available. Please authenticate using the OAuth flow or set OURA_ACCESS_TOKEN environment variable."
      );
    }

    // Check if token is expired and refresh if necessary
    if (this.isTokenExpired(this.cachedTokens)) {
      try {
        const newTokens = await this.refreshAccessToken();
        return newTokens.access_token;
      } catch (error) {
        throw new Error(
          `Token expired and refresh failed: ${error instanceof Error ? error.message : String(error)}`
        );
      }
    }

    return this.cachedTokens.access_token;
  }

  /**
   * Gets the current token information (if available)
   */
  public getTokenInfo(): StoredTokenData | null {
    return this.cachedTokens;
  }

  /**
   * Checks if we have valid credentials (either cached tokens or env token)
   */
  public hasValidCredentials(): boolean {
    return !!(process.env.OURA_PERSONAL_ACCESS_TOKEN || process.env.OURA_ACCESS_TOKEN || this.cachedTokens);
  }

  // ===========================================================================
  // ERROR HANDLING
  // ===========================================================================

  /**
   * Handles OAuth-related errors and provides helpful error messages
   */
  private handleOAuthError(error: unknown, context: string): Error {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<OAuthError>;

      if (axiosError.response?.data) {
        const oauthError = axiosError.response.data;
        const errorMessage = oauthError.error_description || oauthError.error;
        return new Error(`${context}: ${errorMessage}`);
      }

      if (axiosError.response?.status === 401) {
        return new Error(
          `${context}: Unauthorized. Please check your client credentials.`
        );
      }

      if (axiosError.response?.status === 400) {
        return new Error(
          `${context}: Bad request. Check your OAuth parameters.`
        );
      }

      return new Error(
        `${context}: HTTP ${axiosError.response?.status || "error"}`
      );
    }

    return new Error(
      `${context}: ${error instanceof Error ? error.message : String(error)}`
    );
  }
}

// =============================================================================
// FACTORY FUNCTION
// =============================================================================

/**
 * Creates and returns a singleton instance of the OAuth client
 */
let oauthClientInstance: OuraOAuthClient | null = null;

export function getOAuthClient(config?: OAuthConfig): OuraOAuthClient {
  if (!oauthClientInstance) {
    oauthClientInstance = new OuraOAuthClient(config);
  }
  return oauthClientInstance;
}
