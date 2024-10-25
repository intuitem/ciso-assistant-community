import { env } from '$env/dynamic/public';

export const load = () => {
    const LICENSE_EXPIRATION_DAYS = Object.hasOwn(env, 'PUBLIC_LICENSE_EXPIRATION_DAYS')
        ? env.PUBLIC_LICENSE_EXPIRATION_DAYS
        : 30;
    return {
        LICENSE_EXPIRATION_DAYS
    };
};
