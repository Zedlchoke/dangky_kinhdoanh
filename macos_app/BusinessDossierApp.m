#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>

@interface AppDelegate : NSObject <NSApplicationDelegate>
@property NSWindow *window;
@property WKWebView *webView;
@property NSTask *server;
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    [self buildApplicationMenu];
    [self startServer];

    WKWebViewConfiguration *configuration = [[WKWebViewConfiguration alloc] init];
    self.webView = [[WKWebView alloc] initWithFrame:NSMakeRect(0, 0, 1320, 860) configuration:configuration];

    self.window = [[NSWindow alloc] initWithContentRect:NSMakeRect(0, 0, 1320, 860)
                                              styleMask:(NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
                                                backing:NSBackingStoreBuffered
                                                  defer:NO];
    [self.window setTitle:@"Trợ lý hồ sơ đăng ký doanh nghiệp"];
    [self.window center];
    [self.window setContentView:self.webView];
    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];

    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.8 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        NSURL *url = [NSURL URLWithString:@"http://127.0.0.1:8790/"];
        [self.webView loadRequest:[NSURLRequest requestWithURL:url]];
    });
}

- (void)buildApplicationMenu {
    NSMenu *mainMenu = [[NSMenu alloc] initWithTitle:@""];

    NSMenuItem *appItem = [[NSMenuItem alloc] initWithTitle:@"" action:nil keyEquivalent:@""];
    [mainMenu addItem:appItem];
    NSMenu *appMenu = [[NSMenu alloc] initWithTitle:@"Trợ lý hồ sơ ĐKKD"];
    [appMenu addItemWithTitle:@"Thoát Trợ lý hồ sơ ĐKKD" action:@selector(terminate:) keyEquivalent:@"q"];
    [appItem setSubmenu:appMenu];

    NSMenuItem *editItem = [[NSMenuItem alloc] initWithTitle:@"" action:nil keyEquivalent:@""];
    [mainMenu addItem:editItem];
    NSMenu *editMenu = [[NSMenu alloc] initWithTitle:@"Edit"];
    [editMenu addItemWithTitle:@"Undo" action:@selector(undo:) keyEquivalent:@"z"];
    [editMenu addItemWithTitle:@"Redo" action:@selector(redo:) keyEquivalent:@"Z"];
    [editMenu addItem:[NSMenuItem separatorItem]];
    [editMenu addItemWithTitle:@"Cut" action:@selector(cut:) keyEquivalent:@"x"];
    [editMenu addItemWithTitle:@"Copy" action:@selector(copy:) keyEquivalent:@"c"];
    [editMenu addItemWithTitle:@"Paste" action:@selector(paste:) keyEquivalent:@"v"];
    [editMenu addItemWithTitle:@"Select All" action:@selector(selectAll:) keyEquivalent:@"a"];
    [editItem setSubmenu:editMenu];

    [NSApp setMainMenu:mainMenu];
}

- (void)startServer {
    NSString *projectPath = @"/Users/hoangminhlong/Downloads/xuly_dangky_doanhnghiep";
    NSString *pythonPath = @"/Library/Frameworks/Python.framework/Versions/3.13/bin/python3";
    self.server = [[NSTask alloc] init];
    [self.server setLaunchPath:pythonPath];
    [self.server setArguments:@[@"run_app.py", @"8790"]];
    [self.server setCurrentDirectoryPath:projectPath];
    [self.server setStandardOutput:[NSPipe pipe]];
    [self.server setStandardError:[NSPipe pipe]];
    @try {
        [self.server launch];
    } @catch (NSException *exception) {
        NSAlert *alert = [[NSAlert alloc] init];
        [alert setMessageText:@"Không chạy được server local"];
        [alert setInformativeText:[exception reason]];
        [alert runModal];
    }
}

- (void)applicationWillTerminate:(NSNotification *)notification {
    if (self.server && [self.server isRunning]) {
        [self.server terminate];
    }
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    return YES;
}

@end

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        AppDelegate *delegate = [[AppDelegate alloc] init];
        [app setDelegate:delegate];
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];
        [app run];
    }
    return 0;
}
